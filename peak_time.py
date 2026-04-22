import ephem
import math
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from object_visibility import get_ephem_object, OBJECTS

def get_observer(lat, lon):
    obs          = ephem.Observer()
    obs.lat      = str(lat)
    obs.long     = str(lon)
    obs.pressure = 0
    return obs

def get_sun_altitude(obs, dt):
    obs.date = dt.strftime("%Y/%m/%d %H:%M:%S")
    sun      = ephem.Sun()
    sun.compute(obs)
    return math.degrees(float(sun.alt))

def get_moon_altitude_and_phase(obs, dt):
    obs.date = dt.strftime("%Y/%m/%d %H:%M:%S")
    moon     = ephem.Moon()
    moon.compute(obs)
    return math.degrees(float(moon.alt)), moon.phase

def get_object_altitude(obs, dt, object_name):
    obj_info = OBJECTS.get(object_name)
    if not obj_info:
        return None
    obs.date = dt.strftime("%Y/%m/%d %H:%M:%S")
    target   = get_ephem_object(object_name, obj_info)
    target.compute(obs)
    return math.degrees(float(target.alt))

def calculate_darkness_score(sun_alt):
    if sun_alt > 0:       return 0
    elif sun_alt > -6:    return 20
    elif sun_alt > -12:   return 50
    elif sun_alt > -18:   return 80
    else:                 return 100

def calculate_moon_score(moon_alt, moon_phase):
    if moon_alt <= 0:
        return 100
    penalty = (moon_phase / 100) * 40 * (moon_alt / 90)
    return max(0, round(100 - penalty, 1))

def calculate_object_score(object_alt, min_alt=15):
    if object_alt is None or object_alt < min_alt:
        return 0
    if object_alt >= 60:   return 100
    elif object_alt >= 40: return 80
    elif object_alt >= 20: return 60
    else:                  return 40

def calculate_hourly_scores(lat, lon, weather_score,
                             date=None, object_name=None):
    if date is None:
        date = datetime.utcnow()

    obs   = get_observer(lat, lon)
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    hours = []

    for h in range(24):
        dt = start + timedelta(hours=h)

        sun_alt              = get_sun_altitude(obs, dt)
        moon_alt, moon_phase = get_moon_altitude_and_phase(obs, dt)
        darkness_score       = calculate_darkness_score(sun_alt)
        moon_score           = calculate_moon_score(moon_alt, moon_phase)

        obj_alt   = None
        obj_score = None

        if object_name:
            obj_alt   = get_object_altitude(obs, dt, object_name)
            obj_score = calculate_object_score(obj_alt)

            if darkness_score == 0 or obj_score == 0:
                combined = 0
            else:
                combined = round(
                    weather_score * 0.35 +
                    darkness_score * 0.25 +
                    moon_score     * 0.20 +
                    obj_score      * 0.20
                , 1)
        else:
            if darkness_score == 0:
                combined = 0
            else:
                combined = round(
                    weather_score * 0.40 +
                    darkness_score * 0.35 +
                    moon_score     * 0.25
                , 1)

        hours.append({
            "hour":            dt.strftime("%H:00 UTC"),
            "hour_num":        h,
            "sun_altitude":    round(sun_alt, 1),
            "moon_altitude":   round(moon_alt, 1),
            "moon_phase_pct":  round(moon_phase, 1),
            "object_altitude": round(obj_alt, 1) if obj_alt is not None else None,
            "object_score":    obj_score,
            "darkness_score":  darkness_score,
            "moon_score":      moon_score,
            "weather_score":   weather_score,
            "combined_score":  combined,
            "is_dark":         darkness_score >= 80,
            "is_observable":   combined >= 50
        })

    return hours

def get_peak_time(lat, lon, weather_score,
                  date=None, object_name=None):
    hours   = calculate_hourly_scores(
        lat, lon, weather_score, date, object_name)
    df      = pd.DataFrame(hours)
    dark_df = df[df["is_dark"]]

    if dark_df.empty:
        return None

    peak = dark_df.loc[dark_df["combined_score"].idxmax()]

    dark_hours   = dark_df[dark_df["is_observable"]]
    window_start = dark_hours.iloc[0]["hour"]  if not dark_hours.empty else "N/A"
    window_end   = dark_hours.iloc[-1]["hour"] if not dark_hours.empty else "N/A"
    total_hours  = len(dark_hours)

    return {
        "peak_hour":        peak["hour"],
        "peak_score":       peak["combined_score"],
        "peak_darkness":    peak["darkness_score"],
        "peak_moon_score":  peak["moon_score"],
        "peak_obj_alt":     peak.get("object_altitude"),
        "window_start":     window_start,
        "window_end":       window_end,
        "total_good_hours": total_hours,
        "moon_phase_pct":   round(dark_df["moon_phase_pct"].mean(), 1),
        "hourly_data":      hours
    }

def get_all_peak_times(object_name=None):
    conn = sqlite3.connect("data/silver/observatory_weather.db")
    df   = pd.read_sql("""
        SELECT
            o.name       AS observatory,
            o.country,
            o.latitude,
            o.longitude,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS weather_score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
    """, conn)
    conn.close()

    results = []
    for _, row in df.iterrows():
        try:
            peak = get_peak_time(
                row["latitude"],
                row["longitude"],
                row["weather_score"],
                object_name=object_name
            )
            if peak:
                results.append({
                    "observatory":      row["observatory"],
                    "country":          row["country"],
                    "weather_score":    row["weather_score"],
                    "peak_hour":        peak["peak_hour"],
                    "peak_score":       peak["peak_score"],
                    "peak_obj_alt":     peak["peak_obj_alt"],
                    "window_start":     peak["window_start"],
                    "window_end":       peak["window_end"],
                    "total_good_hours": peak["total_good_hours"],
                    "moon_phase_pct":   peak["moon_phase_pct"],
                    "hourly_data":      peak["hourly_data"]
                })
        except Exception as e:
            print(f"  [SKIP] {row['observatory']} — {e}")
            continue

    return pd.DataFrame(results).sort_values(
        "peak_score", ascending=False
    )

if __name__ == "__main__":
    print("\n Testing object-aware peak time...\n")
    peak = get_peak_time(
        19.8207, -155.4681, 95,
        object_name="M42 — Orion Nebula"
    )
    if peak:
        print(f"  Peak hour    : {peak['peak_hour']}")
        print(f"  Peak score   : {peak['peak_score']}")
        print(f"  Object alt   : {peak['peak_obj_alt']}°")
        print(f"  Good window  : {peak['window_start']} → {peak['window_end']}")
        print(f"  Good hours   : {peak['total_good_hours']}h\n")