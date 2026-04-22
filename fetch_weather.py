import requests
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_observatories():
    path = "data/observatory_list.json"
    if not os.path.exists(path):
        print("  [ERROR] data/observatory_list.json not found.")
        print("  Run build_observatory_list.py first.")
        return []
    with open(path, "r") as f:
        return json.load(f)

def _get_hourly_value(data, key):
    try:
        values   = data.get("hourly", {}).get(key, [])
        now_hour = datetime.utcnow().hour
        return values[now_hour] if values else None
    except Exception:
        return None

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
        "hourly": [
            "windspeed_250hPa",
            "temperature_500hPa",
            "temperature_850hPa",
            "relativehumidity_1000hPa",
            "relativehumidity_700hPa",
            "relativehumidity_500hPa",
            "relativehumidity_300hPa",
        ],
        "wind_speed_unit": "ms",
        "forecast_days":   1
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data    = response.json()
        current = data["current"]

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
            "jet_stream_ms":    _get_hourly_value(
                data, "windspeed_250hPa"),
            "temp_500hpa":      _get_hourly_value(
                data, "temperature_500hPa"),
            "temp_850hpa":      _get_hourly_value(
                data, "temperature_850hPa"),
            "rh_1000hpa":       _get_hourly_value(
                data, "relativehumidity_1000hPa"),
            "rh_700hpa":        _get_hourly_value(
                data, "relativehumidity_700hPa"),
            "rh_500hpa":        _get_hourly_value(
                data, "relativehumidity_500hPa"),
            "rh_300hpa":        _get_hourly_value(
                data, "relativehumidity_300hPa"),
        }

    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {observatory['name']}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR]   {observatory['name']} — {e}")
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
    results, failed = fetch_all_parallel(
        observatories, max_workers=20)
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