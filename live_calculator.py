import ephem
import math
from datetime import datetime
from atmospheric import get_full_atmospheric_analysis
from observing_window import get_all_windows
from peak_time import get_peak_time

def calculate_live_conditions(obs_row):
    """
    Calculate all live conditions for a single observatory.
    Takes a pandas row from the weather dataframe.
    Returns a complete dict of all live calculations.
    """
    lat     = float(obs_row["latitude"])
    lon     = float(obs_row["longitude"])
    alt     = float(obs_row["altitude_m"])
    w_score = float(obs_row["observation_score"])

    # ── Atmospheric analysis ──────────────────────────────
    atm = get_full_atmospheric_analysis({
        "temperature_c":    obs_row.get("temperature_c"),
        "wind_speed_ms":    obs_row.get("wind_speed_ms"),
        "humidity_pct":     obs_row.get("humidity_pct"),
        "altitude_m":       alt,
        "surface_pressure": obs_row.get("surface_pressure"),
        "jet_stream_ms":    obs_row.get("jet_stream_ms"),
        "latitude":         lat
    })

    # ── Observing window ──────────────────────────────────
    # ── Observing window ──────────────────────────────────
    try:
        import pandas as pd
        single_df = pd.DataFrame([{
            "observatory":       obs_row["observatory"],
            "country":           obs_row.get(
                "country", "Unknown"),
            "latitude":          lat,
            "longitude":         lon,
            "altitude_m":        alt,
            "mpc_code":          obs_row.get("mpc_code", ""),
            "observation_score": w_score,
            "cloud_cover_pct":   obs_row.get(
                "cloud_cover_pct"),
            "humidity_pct":      obs_row.get("humidity_pct"),
            "wind_speed_ms":     obs_row.get("wind_speed_ms"),
            "temperature_c":     obs_row.get("temperature_c"),
        }])
        from observing_window import get_all_windows
        wins = get_all_windows(single_df)
        win  = wins.iloc[0].to_dict() if not wins.empty else {}
    except Exception:
        win = {
            "dark_start":     "N/A",
            "dark_end":       "N/A",
            "dark_hours":     0,
            "moon_rise":      "N/A",
            "moon_set":       "N/A",
            "final_score":    0,
            "moon_phase":     "Unknown",
            "moon_phase_pct": 0
        }
    # ── Peak time ─────────────────────────────────────────
    try:
        peak = get_peak_time(lat, lon, w_score)
    except Exception:
        peak = None

    # ── Current sky position ──────────────────────────────
    observer          = ephem.Observer()
    observer.lat      = str(lat)
    observer.long     = str(lon)
    observer.date     = datetime.utcnow().strftime(
        "%Y/%m/%d %H:%M:%S")
    observer.pressure = 0

    moon = ephem.Moon()
    moon.compute(observer)
    moon_alt = math.degrees(float(moon.alt))
    moon_az  = math.degrees(float(moon.az))

    sun = ephem.Sun()
    sun.compute(observer)
    sun_alt = math.degrees(float(sun.alt))

    # ── Sky state ─────────────────────────────────────────
    if sun_alt > 0:
        sky_state = "Daytime ☀️"
    elif sun_alt > -6:
        sky_state = "Civil twilight 🌆"
    elif sun_alt > -12:
        sky_state = "Nautical twilight 🌇"
    elif sun_alt > -18:
        sky_state = "Astronomical twilight 🌃"
    else:
        sky_state = "Astronomical night 🌑"

    is_dark = sun_alt <= -18

    return {
        "observatory":       obs_row["observatory"],
        "country":           obs_row.get(
            "country", "Unknown"),
        "latitude":          lat,
        "longitude":         lon,
        "altitude_m":        alt,
        "fetch_datetime":    obs_row.get("fetch_datetime"),
        "observation_score": w_score,
        "cloud_cover_pct":   obs_row.get("cloud_cover_pct"),
        "humidity_pct":      obs_row.get("humidity_pct"),
        "wind_speed_ms":     obs_row.get("wind_speed_ms"),
        "temperature_c":     obs_row.get("temperature_c"),
        "precipitation_mm":  obs_row.get("precipitation_mm"),
        "seeing_arcsec":     atm["seeing_arcsec"],
        "seeing_quality":    atm["seeing_quality"],
        "pwv_mm":            atm["pwv_mm"],
        "pwv_quality":       atm["pwv_quality"],
        "jet_stream_ms":     atm["jet_stream_ms"],
        "jet_impact":        atm["jet_impact"],
        "sun_altitude":      round(sun_alt, 1),
        "moon_altitude":     round(moon_alt, 1),
        "moon_azimuth":      round(moon_az, 1),
        "moon_phase_pct":    round(moon.phase, 1),
        "sky_state":         sky_state,
        "is_dark":           is_dark,
        "dark_start":        win.get("dark_start", "N/A"),
        "dark_end":          win.get("dark_end", "N/A"),
        "dark_hours":        win.get("dark_hours", 0),
        "moon_rise":         win.get("moon_rise", "N/A"),
        "moon_set":          win.get("moon_set", "N/A"),
        "final_score":       win.get("final_score", 0),
        "peak_hour":         peak["peak_hour"]
                             if peak else "N/A",
        "peak_score":        peak["peak_score"]
                             if peak else 0,
        "total_good_hours":  peak["total_good_hours"]
                             if peak else 0,
        "hourly_data":       peak["hourly_data"]
                             if peak else [],
        "calculated_at":     datetime.utcnow().strftime(
            "%Y-%m-%d %H:%M UTC")
    }