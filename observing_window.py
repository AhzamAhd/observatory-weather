import ephem
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import math

def get_moon_phase(date):
    moon = ephem.Moon(date.strftime("%Y/%m/%d"))
    phase = moon.phase
    if phase < 10:   return phase, "New Moon"
    elif phase < 35: return phase, "Crescent"
    elif phase < 60: return phase, "Quarter"
    elif phase < 85: return phase, "Gibbous"
    else:            return phase, "Full Moon"

def get_twilight_times(lat, lon, date):
    obs = ephem.Observer()
    obs.lat  = str(lat)
    obs.long = str(lon)
    obs.date = date.strftime("%Y/%m/%d 12:00:00")

    sun = ephem.Sun()

    try:
        obs.horizon = "-18"  # astronomical twilight
        astro_dusk  = obs.next_setting(sun, use_center=True).datetime()
        astro_dawn  = obs.next_rising(sun,  use_center=True).datetime()
    except Exception:
        astro_dusk = date.replace(hour=18, minute=0)
        astro_dawn = date.replace(hour=6,  minute=0) + timedelta(days=1)

    try:
        obs.horizon = "0"
        moon        = ephem.Moon()
        moon_rise   = obs.next_rising(moon).datetime()
        moon_set    = obs.next_setting(moon).datetime()
    except Exception:
        moon_rise = None
        moon_set  = None

    return astro_dusk, astro_dawn, moon_rise, moon_set

def calculate_moon_penalty(moon_phase_pct, moon_rise, moon_set,
                            window_start, window_end):
    moon_up = False
    if moon_rise and moon_set:
        if moon_rise < moon_set:
            moon_up = moon_rise < window_end and moon_set > window_start
        else:
            moon_up = True

    if not moon_up:
        return 0

    if moon_phase_pct > 85:   return 40
    elif moon_phase_pct > 60: return 25
    elif moon_phase_pct > 35: return 15
    elif moon_phase_pct > 10: return 5
    return 0

def get_observing_windows(lat, lon, obs_score, date=None):
    if date is None:
        date = datetime.utcnow()

    moon_pct, moon_name = get_moon_phase(date)
    astro_dusk, astro_dawn, moon_rise, moon_set = get_twilight_times(
        lat, lon, date
    )

    dark_hours = (astro_dawn - astro_dusk).total_seconds() / 3600
    if dark_hours < 0:
        dark_hours += 24

    window_start = astro_dusk
    window_end   = astro_dawn

    moon_penalty = calculate_moon_penalty(
        moon_pct, moon_rise, moon_set, window_start, window_end
    )

    final_score = max(0, obs_score - moon_penalty)

    if final_score >= 80:   quality = "Excellent"
    elif final_score >= 60: quality = "Good"
    elif final_score >= 40: quality = "Marginal"
    else:                   quality = "Poor"

    return {
        "dark_start":    astro_dusk.strftime("%H:%M UTC"),
        "dark_end":      astro_dawn.strftime("%H:%M UTC"),
        "dark_hours":    round(dark_hours, 1),
        "moon_phase":    moon_name,
        "moon_phase_pct": round(moon_pct, 1),
        "moon_rise":     moon_rise.strftime("%H:%M UTC") if moon_rise else "N/A",
        "moon_set":      moon_set.strftime("%H:%M UTC")  if moon_set  else "N/A",
        "moon_penalty":  moon_penalty,
        "final_score":   final_score,
        "quality":       quality
    }

def get_all_windows():
    conn = sqlite3.connect("data/silver/observatory_weather.db")
    df   = pd.read_sql("""
        SELECT
            o.name        AS observatory,
            o.country,
            o.latitude,
            o.longitude,
            o.altitude_m,
            w.fetch_date,
            w.fetch_time,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS observation_score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        ORDER BY observation_score DESC
    """, conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        try:
            window = get_observing_windows(
                row["latitude"],
                row["longitude"],
                row["observation_score"]
            )
            results.append({
                "observatory":      row["observatory"],
                "country":          row["country"],
                "latitude":         row["latitude"],
                "longitude":        row["longitude"],
                "weather_score":    row["observation_score"],
                "dark_start":       window["dark_start"],
                "dark_end":         window["dark_end"],
                "dark_hours":       window["dark_hours"],
                "moon_phase":       window["moon_phase"],
                "moon_phase_pct":   window["moon_phase_pct"],
                "moon_rise":        window["moon_rise"],
                "moon_set":         window["moon_set"],
                "moon_penalty":     window["moon_penalty"],
                "final_score":      window["final_score"],
                "quality":          window["quality"]
            })
        except Exception as e:
            print(f"  [SKIP] {row['observatory']} — {e}")
            continue

    return pd.DataFrame(results).sort_values("final_score", ascending=False)

if __name__ == "__main__":
    print("\n Calculating observing windows...\n")
    df = get_all_windows()
    print(df[["observatory", "dark_start", "dark_end",
              "dark_hours", "moon_phase", "final_score",
              "quality"]].to_string(index=False))
    print(f"\n Best site tonight: {df.iloc[0]['observatory']}")
    print(f" Window: {df.iloc[0]['dark_start']} → {df.iloc[0]['dark_end']}")
    print(f" Score:  {df.iloc[0]['final_score']} / 100 [{df.iloc[0]['quality']}]\n")