import requests
import json
import os
import sys
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Observatory names contain non-ASCII characters (e.g. "Skalnaté pleso"). On
# Windows the console defaults to a cp1252 codec that raises UnicodeEncodeError
# when such a name is printed, which would abort the whole fetch. Force UTF-8
# with a replacing error handler so progress logging can never crash the run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def _nearest_hour_profile(hourly):
    """From Open-Meteo's hourly block, return a dict of each field's value at
    the hour nearest the current UTC time. Empty dict if no hourly data."""
    times = hourly.get("time") or []
    if not times:
        return {}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Open-Meteo hourly times are "YYYY-MM-DDTHH:MM" (local-to-request, but we
    # only need the nearest index, so parse naively and pick the closest).
    best_i, best_dt = 0, None
    for i, t in enumerate(times):
        try:
            dt = datetime.strptime(t, "%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            continue
        diff = abs((dt - now).total_seconds())
        if best_dt is None or diff < best_dt:
            best_dt, best_i = diff, i
    out = {}
    for key, values in hourly.items():
        if key == "time":
            continue
        if isinstance(values, list) and best_i < len(values):
            out[key] = values[best_i]
    return out


def load_observatories():
    path = "data/observatory_list.json"
    if not os.path.exists(path):
        print("  [ERROR] data/observatory_list.json not found.")
        print("  Run build_observatory_list.py first.")
        return []
    with open(path, "r") as f:
        return json.load(f)

def fetch_weather(observatory):
    url    = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":  observatory["latitude"],
        "longitude": observatory["longitude"],
        "current": [
            "cloudcover",
            "relativehumidity_2m",
            "windspeed_10m",
            "temperature_2m",
            "precipitation",
            "surface_pressure",
            "dewpoint_2m",
            "windspeed_80m",
            "windspeed_120m",
        ],
        # Pressure-level (vertical profile) fields — needed for the Tatarski
        # seeing model's real potential-temperature gradient and wind shear.
        # These come from the hourly endpoint; we take the hour nearest the
        # fetch time. temp/geopotential at 850 & 500 hPa give dTheta/dz; wind at
        # 850 & 250 hPa gives free-atmosphere shear + the jet.
        "hourly": [
            "temperature_850hPa",
            "temperature_700hPa",
            "temperature_500hPa",
            "geopotential_height_850hPa",
            "geopotential_height_500hPa",
            "wind_speed_850hPa",
            "wind_speed_250hPa",
            "relative_humidity_850hPa",
            "relative_humidity_500hPa",
            # Model-computed total-column precipitable water (sea-level column);
            # scaled to site altitude when used. Far more reliable than deriving
            # PWV from the coarse 2-3 node humidity profile.
            "total_column_integrated_water_vapour",
        ],
        "wind_speed_unit": "ms",
        "forecast_days":   1
    }

    # Retry with backoff, mainly to ride out Open-Meteo 429 rate limits.
    for attempt in range(4):
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                # Honour Retry-After if present, else exponential backoff.
                wait = float(response.headers.get("Retry-After", 2 ** attempt))
                time.sleep(min(wait, 15))
                continue
            response.raise_for_status()
            payload = response.json()
            current = payload["current"]

            # Pick the hourly index nearest the current UTC time so the vertical
            # profile matches the surface reading.
            prof = _nearest_hour_profile(payload.get("hourly", {}))

            return {
                "observatory_name": observatory["name"],
                "country":          observatory.get("country", "Unknown"),
                "latitude":         observatory["latitude"],
                "longitude":        observatory["longitude"],
                "altitude_m":       observatory.get("altitude_m", 0),
                "mpc_code":         observatory.get("code", ""),
                "cloud_cover_pct":  current.get("cloudcover"),
                "humidity_pct":     current.get("relativehumidity_2m"),
                "wind_speed_ms":    current.get("windspeed_10m"),
                "temperature_c":    current.get("temperature_2m"),
                "precipitation_mm": current.get("precipitation"),
                "surface_pressure": current.get("surface_pressure"),
                "dewpoint_c":       current.get("dewpoint_2m"),
                "wind_speed_80m":   current.get("windspeed_80m"),
                "wind_speed_120m":  current.get("windspeed_120m"),
                # Vertical profile (for the Tatarski seeing model):
                "temp_850hpa":      prof.get("temperature_850hPa"),
                "temp_700hpa":      prof.get("temperature_700hPa"),
                "temp_500hpa":      prof.get("temperature_500hPa"),
                "geopot_850hpa":    prof.get("geopotential_height_850hPa"),
                "geopot_500hpa":    prof.get("geopotential_height_500hPa"),
                "wind_850hpa":      prof.get("wind_speed_850hPa"),
                "rh_850hpa":        prof.get("relative_humidity_850hPa"),
                "rh_500hpa":        prof.get("relative_humidity_500hPa"),
                "pwv_column":       prof.get("total_column_integrated_water_vapour"),
                # 250 hPa wind is the jet-stream proxy at that level.
                "jet_stream_ms":    prof.get("wind_speed_250hPa"),
            }

        except requests.exceptions.Timeout:
            time.sleep(2 ** attempt)
            continue
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR]   {observatory['name']} — {e}")
            return None

    print(f"  [RATELIMIT] {observatory['name']} — gave up after retries")
    return None

def fetch_all_parallel(observatories, max_workers=20):
    results = []
    failed  = 0
    print(
        f"  Fetching {len(observatories)} observatories "
        f"in parallel ({max_workers} threads)...\n"
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_obs = {
            executor.submit(fetch_weather, obs): obs
            for obs in observatories
        }
        completed = 0
        for future in as_completed(future_to_obs):
            completed += 1
            result = future.result()
            if result:
                results.append(result)
                print(
                    f"  [{completed:02d}/{len(observatories)}] "
                    f"{result['observatory_name'][:50]:<50} "
                    f"cloud={result['cloud_cover_pct']}%  "
                    f"pwv_ready={'yes' if result.get('surface_pressure') else 'no'}"
                )
            else:
                failed += 1
    return results, failed

def main():
    print(
        f"\n Starting parallel fetch — "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
    )
    observatories = load_observatories()
    if not observatories:
        return

    print(f"  Loaded {len(observatories)} observatories\n")
    # 24 threads: the list grew to ~2,600 sites, so we parallelise more to fit
    # the CI time budget. The per-request 429 retries with backoff still keep us
    # within Open-Meteo's free-tier rate limit during bursts.
    results, failed = fetch_all_parallel(
        observatories, max_workers=24)
    print(
        f"\n  Fetch complete — "
        f"{len(results)} succeeded, {failed} failed\n"
    )

    os.makedirs("data/bronze", exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"data/bronze/raw_weather_{date_str}.json"

    with open(filename, "w") as f:
        json.dump(results, f, indent=2)

    print(f"  Saved {len(results)} records → {filename}\n")

if __name__ == "__main__":
    main()