import ephem
import math
import requests
from datetime import datetime, timezone, timedelta


# ── Fetch TLE data ────────────────────────────────────────────────
def fetch_tle(url):
    """Fetch TLE data from Celestrak with proper headers."""
    try:
        headers  = {"User-Agent": "Observatory-Weather-Tracker/1.0"}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  [WARN] TLE fetch failed: {e}")
        return None


# ── Parse TLE text ────────────────────────────────────────────────
def parse_tle(text):
    """Parse TLE text into list of (name, line1, line2)."""
    satellites = []
    lines      = [l.strip() for l in text.strip().split("\n")
                  if l.strip()]
    i = 0
    while i < len(lines):
        if (i + 2 < len(lines) and
                lines[i+1].startswith("1 ") and
                lines[i+2].startswith("2 ")):
            satellites.append((
                lines[i].strip(),
                lines[i+1].strip(),
                lines[i+2].strip()
            ))
            i += 3
        else:
            i += 1
    return satellites


# ── TLE sources ───────────────────────────────────────────────────
def get_iss_tle():
    """Get current ISS TLE using new Celestrak GP API."""
    urls = [
        "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE",
        "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle",
    ]
    for url in urls:
        text = fetch_tle(url)
        if text:
            sats = parse_tle(text)
            if sats:
                return sats[0]

    print("  [WARN] Could not fetch ISS TLE — using fallback")
    # Recent fallback TLE — will be slightly outdated
    return (
        "ISS (ZARYA)",
        "1 25544U 98067A   24127.82853009  .00015698  00000+0  27310-3 0  9995",
        "2 25544  51.6393 160.4574 0003580 140.6673 205.7250 15.50957674452123"
    )


def get_station_satellites():
    """Get TLE data for all space stations."""
    url  = ("https://celestrak.org/NORAD/elements/"
            "gp.php?GROUP=stations&FORMAT=TLE")
    text = fetch_tle(url)
    if text:
        return parse_tle(text)
    return []


def get_visual_satellites():
    """Get TLE data for visually bright satellites."""
    url  = ("https://celestrak.org/NORAD/elements/"
            "gp.php?GROUP=visual&FORMAT=TLE")
    text = fetch_tle(url)
    if text:
        return parse_tle(text)
    return []


# ── Helper functions ──────────────────────────────────────────────
def azimuth_to_direction(az):
    """Convert azimuth degrees to compass direction."""
    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]
    idx = round(az / 22.5) % 16
    return directions[idx]


def estimate_magnitude(satellite_name, max_alt_deg):
    """Estimate visual magnitude of a satellite pass."""
    name_lower = satellite_name.lower()
    if "iss" in name_lower:
        base = -3.0
    elif "tiangong" in name_lower or "css" in name_lower:
        base = -1.5
    elif "hubble" in name_lower:
        base = 1.5
    elif "starlink" in name_lower:
        base = 3.5
    else:
        base = 3.0
    alt_bonus = (max_alt_deg - 45) * 0.02
    return round(base - alt_bonus, 1)


def magnitude_visibility(mag):
    """Describe visibility from magnitude."""
    if mag < -3:   return "Extremely bright — unmissable"
    elif mag < -1: return "Very bright — easy to see"
    elif mag < 1:  return "Bright — clearly visible"
    elif mag < 3:  return "Visible to naked eye"
    elif mag < 5:  return "Faint — dark sky needed"
    else:          return "Very faint — binoculars needed"


def magnitude_emoji(mag):
    """Emoji for brightness level."""
    if mag < -1:  return "🌟"
    elif mag < 1: return "⭐"
    elif mag < 3: return "✨"
    else:         return "🔭"


# ── Pass calculation ──────────────────────────────────────────────
def calculate_passes(
    name, line1, line2,
    lat, lon, alt_m,
    hours_ahead=24,
    min_altitude=10
):
    try:
        observer           = ephem.Observer()
        observer.lat       = str(lat)
        observer.long      = str(lon)
        observer.elevation = float(alt_m)
        observer.pressure  = 0
        observer.horizon   = "0"  # Find ALL passes first

        satellite   = ephem.readtle(name, line1, line2)
        now         = datetime.utcnow()
        end         = now + timedelta(hours=hours_ahead)
        passes      = []
        max_passes  = 10
        search_date = ephem.Date(
            now.strftime("%Y/%m/%d %H:%M:%S"))

        for _ in range(50):  # Max iterations
            if len(passes) >= max_passes:
                break

            try:
                observer.date = search_date
                satellite.compute(observer)

                (rise_time, rise_az,
                 max_time,  max_alt,
                 set_time,  set_az) = observer.next_pass(satellite)

                if rise_time is None:
                    break

                rise_dt     = ephem.Date(rise_time).datetime()
                set_dt      = ephem.Date(set_time).datetime()
                max_dt      = ephem.Date(max_time).datetime()
                max_alt_deg = math.degrees(float(max_alt))

                # Stop if past our window
                if rise_dt > end:
                    break

                # Only keep passes above minimum altitude
                if max_alt_deg >= min_altitude:
                    duration_s = max(
                        0, (set_dt - rise_dt).total_seconds())
                    mag      = estimate_magnitude(
                        name, max_alt_deg)
                    rise_dir = azimuth_to_direction(
                        math.degrees(float(rise_az)))
                    set_dir  = azimuth_to_direction(
                        math.degrees(float(set_az)))

                    # Check darkness
                    sun = ephem.Sun()
                    observer.date = ephem.Date(max_time)
                    sun.compute(observer)
                    sun_alt    = math.degrees(float(sun.alt))
                    is_night   = sun_alt < -6
                    is_visible = (is_night and
                                  max_alt_deg >= min_altitude)

                    passes.append({
                        "name":         name,
                        "rise_time":    rise_dt.strftime(
                            "%H:%M UTC"),
                        "rise_time_dt": rise_dt,
                        "max_time":     max_dt.strftime(
                            "%H:%M UTC"),
                        "set_time":     set_dt.strftime(
                            "%H:%M UTC"),
                        "date_str":     rise_dt.strftime(
                            "%Y-%m-%d"),
                        "day_name":     rise_dt.strftime(
                            "%A"),
                        "rise_az":      round(math.degrees(
                            float(rise_az)), 1),
                        "max_alt":      round(max_alt_deg, 1),
                        "set_az":       round(math.degrees(
                            float(set_az)), 1),
                        "rise_dir":     rise_dir,
                        "set_dir":      set_dir,
                        "duration_s":   int(duration_s),
                        "duration_str": (
                            f"{int(duration_s//60)}m "
                            f"{int(duration_s%60)}s"),
                        "magnitude":    mag,
                        "mag_desc":     magnitude_visibility(mag),
                        "mag_emoji":    magnitude_emoji(mag),
                        "is_visible":   is_visible,
                        "is_night":     is_night,
                        "sun_alt":      round(sun_alt, 1),
                    })

                # Always advance past this pass
                search_date = ephem.Date(set_time) + ephem.minute

            except Exception as e:
                search_date = (ephem.Date(search_date)
                               + ephem.hour)
                continue

        return passes

    except Exception as e:
        print(f"  [WARN] Pass calculation failed "
              f"for {name}: {e}")
        return []


# ── Current position ──────────────────────────────────────────────
def get_current_position(name, line1, line2,
                         lat, lon, alt_m):
    """Get current satellite position in sky."""
    try:
        observer           = ephem.Observer()
        observer.lat       = str(lat)
        observer.long      = str(lon)
        observer.elevation = float(alt_m)
        observer.pressure  = 0
        observer.date      = datetime.now(
            timezone.utc).strftime("%Y/%m/%d %H:%M:%S")

        satellite = ephem.readtle(name, line1, line2)
        satellite.compute(observer)

        alt = math.degrees(float(satellite.alt))
        az  = math.degrees(float(satellite.az))
        rng = satellite.range / 1000  # km

        return {
            "altitude":      round(alt, 1),
            "azimuth":       round(az, 1),
            "direction":     azimuth_to_direction(az),
            "range_km":      round(rng, 0),
            "visible":       alt > 0,
            "sublong":       round(
                math.degrees(float(satellite.sublong)), 2),
            "sublat":        round(
                math.degrees(float(satellite.sublat)), 2),
        }
    except Exception:
        return None


# ── Main function ─────────────────────────────────────────────────
def get_all_passes(lat, lon, alt_m, hours_ahead=24):
    """
    Get passes for ISS and other key satellites.
    Main function called by dashboard.
    """
    print(f"\n  Calculating satellite passes "
          f"for next {hours_ahead}h...")
    results = {}

    # ISS
    print("  Fetching ISS TLE...")
    iss_name, iss_l1, iss_l2 = get_iss_tle()
    print(f"  Got TLE: {iss_name}")

    iss_passes = calculate_passes(
        iss_name, iss_l1, iss_l2,
        lat, lon, alt_m, hours_ahead
    )
    iss_pos = get_current_position(
        iss_name, iss_l1, iss_l2,
        lat, lon, alt_m
    )

    results["ISS"] = {
        "name":     "ISS (International Space Station)",
        "norad":    25544,
        "passes":   iss_passes,
        "position": iss_pos,
        "tle":      (iss_name, iss_l1, iss_l2),
        "color":    "#FFD700",
        "icon":     "🛸"
    }

    # Other space stations
    print("  Fetching space station TLEs...")
    station_sats = get_station_satellites()
    print(f"  Found {len(station_sats)} station satellites")

    added = 0
    for sat_name, l1, l2 in station_sats:
        if added >= 4:
            break
        if "ISS" in sat_name.upper():
            continue

        passes = calculate_passes(
            sat_name, l1, l2,
            lat, lon, alt_m,
            hours_ahead, min_altitude=10
        )

        if passes:
            pos = get_current_position(
                sat_name, l1, l2, lat, lon, alt_m)
            results[sat_name] = {
                "name":     sat_name,
                "norad":    None,
                "passes":   passes,
                "position": pos,
                "tle":      (sat_name, l1, l2),
                "color":    "#4ECDC4",
                "icon":     "🛰️"
            }
            added += 1

    visible_count = sum(
        1 for sat in results.values()
        for p in sat["passes"]
        if p["is_visible"]
    )
    print(f"  Found passes for {len(results)} satellites")
    print(f"  {visible_count} visible passes tonight")
    return results


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Satellite Pass Predictor")
    print("  Location: Mauna Kea, Hawaii\n")

    lat, lon, alt = 19.8207, -155.4681, 4205
    results       = get_all_passes(lat, lon, alt,
                                   hours_ahead=24)

    for sat_key, sat_data in results.items():
        passes = sat_data["passes"]
        pos    = sat_data["position"]

        print(f"\n  {sat_data['icon']} "
              f"{sat_data['name']}")
        print(f"  {len(passes)} passes in next 24h")

        if pos:
            print(f"  Current position: "
                  f"Alt {pos['altitude']}° "
                  f"Az {pos['azimuth']}° "
                  f"({pos['direction']}) "
                  f"Range {pos['range_km']}km")

        for p in passes[:3]:
            visible = "✅ VISIBLE" if p["is_visible"] else "⛅ Daylight"
            print(
                f"    {p['day_name']} "
                f"{p['rise_time']} → {p['set_time']} · "
                f"Max {p['max_alt']}° · "
                f"Mag {p['magnitude']} "
                f"{p['mag_emoji']} · "
                f"{p['rise_dir']} → {p['set_dir']} · "
                f"{visible}"
            )

    print()