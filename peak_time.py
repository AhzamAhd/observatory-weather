import ephem
import math
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

def get_observer(lat, lon):
    obs = ephem.Observer()
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

def calculate_darkness_score(sun_alt):
    if sun_alt > 0:       return 0    # daytime
    elif sun_alt > -6:    return 20   # civil twilight
    elif sun_alt > -12:   return 50   # nautical twilight
    elif sun_alt > -18:   return 80   # astronomical twilight
    else:                 return 100  # full darkness

def calculate_moon_score(moon_alt, moon_phase):
    if moon_alt <= 0:
        return 100   # moon below horizon — no penalty
    penalty = (moon_phase / 100) * 40 * (moon_alt / 90)
    return max(0, round(100 - penalty, 1))

def calculate_hourly_scores(lat, lon, weather_score, date=None):
    if date is None:
        date = datetime.utcnow()

    obs = get_observer(lat, lon)

    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    hours = []

    for h in range(24):
        dt = start + timedelta(hours=h)

        sun_alt                  = get_sun_altitude(obs, dt)
        moon_alt, moon_phase     = get_moon_altitude_and_phase(obs, dt)
        darkness_score           = calculate_darkness_score(sun_alt)
        moon_score               = calculate_moon_score(moon_alt, moon_phase)

        if darkness_score == 0:
            combined = 0   # daytime — no observing
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
            "darkness_score":  darkness_score,
            "moon_score":      moon_score,
            "weather_score":   weather_score,
            "combined_score":  combined,
            "is_dark":         darkness_score >= 80,
            "is_observable":   combined >= 50
        })

    return hours

def get_peak_time(lat, lon, weather_score, date=None):
    hours   = calculate_hourly_scores(lat, lon, weather_score, date)
    df      = pd.DataFrame(hours)
    dark_df = df[df["is_dark"]]

    if dark_df.empty:
        return None

    peak = dark_df.loc[dark_df["combined_score"].idxmax()]

    dark_hours    = dark_df[dark_df["is_observable"]]
    window_start  = dark_hours.iloc[0]["hour"]  if not dark_hours.empty else "N/A"
    window_end    = dark_hours.iloc[-1]["hour"] if not dark_hours.empty else "N/A"
    total_hours   = len(dark_hours)

    return {
        "peak_hour":          peak["hour"],
        "peak_score":         peak["combined_score"],
        "peak_darkness":      peak["darkness_score"],
        "peak_moon_score":    peak["moon_score"],
        "window_start":       window_start,
        "window_end":         window_end,
        "total_good_hours":   total_hours,
        "moon_phase_pct":     round(dark_df["moon_phase_pct"].mean(), 1),
        "hourly_data":        hours
    }

def get_all_peak_times():
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
                row["weather_score"]
            )
            if peak:
                results.append({
                    "observatory":      row["observatory"],
                    "country":          row["country"],
                    "weather_score":    row["weather_score"],
                    "peak_hour":        peak["peak_hour"],
                    "peak_score":       peak["peak_score"],
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
    print("\n Testing peak time calculator...\n")
    peak = get_peak_time(19.8207, -155.4681, 95)
    if peak:
        print(f"  Peak hour       : {peak['peak_hour']}")
        print(f"  Peak score      : {peak['peak_score']}")
        print(f"  Good window     : {peak['window_start']} → {peak['window_end']}")
        print(f"  Total good hours: {peak['total_good_hours']}h")
        print(f"  Moon phase      : {peak['moon_phase_pct']}%\n")