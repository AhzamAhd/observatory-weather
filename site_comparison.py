import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from atmospheric import get_full_atmospheric_analysis

def get_site_data(observatory_names, days=30):
    """
    Fetch all data for selected observatories.
    """
    placeholders = ",".join(["?" for _ in observatory_names])
    cutoff       = (datetime.utcnow() - timedelta(days=days)
                    ).strftime("%Y-%m-%d")

    conn = sqlite3.connect("data/silver/observatory_weather.db")
    df   = pd.read_sql(f"""
        SELECT
            o.name          AS observatory,
            o.country,
            o.altitude_m,
            o.latitude,
            o.longitude,
            w.fetch_date,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            w.surface_pressure,
            w.jet_stream_ms,
            w.dewpoint_c,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS daily_score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        WHERE o.name IN ({placeholders})
        AND w.fetch_date >= ?
        ORDER BY o.name, w.fetch_date
    """, conn, params=observatory_names + [cutoff])
    conn.close()
    return df

def get_current_data(observatory_names):
    """
    Fetch today's readings for selected observatories.
    """
    placeholders = ",".join(["?" for _ in observatory_names])
    conn         = sqlite3.connect(
        "data/silver/observatory_weather.db")
    df = pd.read_sql(f"""
        SELECT
            o.name          AS observatory,
            o.country,
            o.altitude_m,
            o.latitude,
            o.longitude,
            w.fetch_date,
            w.fetch_time,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            w.surface_pressure,
            w.jet_stream_ms,
            w.dewpoint_c,
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
        WHERE o.name IN ({placeholders})
        ORDER BY observation_score DESC
    """, conn, params=observatory_names)
    conn.close()
    return df

def compare_sites(observatory_names, days=30):
    """
    Full comparison of selected observatories.
    Returns current snapshot + historical stats + atmospheric.
    """
    current  = get_current_data(observatory_names)
    historic = get_site_data(observatory_names, days)

    results = []

    for obs in observatory_names:
        cur_row  = current[current["observatory"] == obs]
        hist_row = historic[historic["observatory"] == obs]

        if cur_row.empty:
            continue

        cur = cur_row.iloc[0]

        # Atmospheric analysis
        atm = get_full_atmospheric_analysis({
            "temperature_c":    cur.get("temperature_c"),
            "wind_speed_ms":    cur.get("wind_speed_ms"),
            "humidity_pct":     cur.get("humidity_pct"),
            "altitude_m":       cur.get("altitude_m", 0),
            "surface_pressure": cur.get("surface_pressure"),
            "jet_stream_ms":    cur.get("jet_stream_ms"),
            "latitude":         cur.get("latitude", 0)
        })

        # Historical stats
        if not hist_row.empty:
            avg_score       = round(
                hist_row["daily_score"].mean(), 1)
            pct_excellent   = round(
                len(hist_row[hist_row["daily_score"] >= 80])
                / len(hist_row) * 100, 1)
            pct_poor        = round(
                len(hist_row[hist_row["daily_score"] < 40])
                / len(hist_row) * 100, 1)
            consistency     = round(
                max(0, 100 - hist_row["daily_score"].std() * 2),
                1)
            daily_scores    = hist_row[[
                "fetch_date", "daily_score"]
            ].to_dict("records")
        else:
            avg_score     = cur["observation_score"]
            pct_excellent = 0
            pct_poor      = 0
            consistency   = 0
            daily_scores  = []

        results.append({
            "observatory":      obs,
            "country":          cur["country"],
            "altitude_m":       cur["altitude_m"],
            "latitude":         cur["latitude"],
            "longitude":        cur["longitude"],
            "today_score":      cur["observation_score"],
            "cloud_cover_pct":  cur["cloud_cover_pct"],
            "humidity_pct":     cur["humidity_pct"],
            "wind_speed_ms":    cur["wind_speed_ms"],
            "temperature_c":    cur["temperature_c"],
            "avg_score":        avg_score,
            "pct_excellent":    pct_excellent,
            "pct_poor":         pct_poor,
            "consistency":      consistency,
            "days_of_data":     len(hist_row),
            "daily_scores":     daily_scores,
            "seeing_arcsec":    atm["seeing_arcsec"],
            "seeing_quality":   atm["seeing_quality"],
            "pwv_mm":           atm["pwv_mm"],
            "pwv_quality":      atm["pwv_quality"],
            "jet_stream_ms":    atm["jet_stream_ms"],
            "jet_impact":       atm["jet_impact"],
        })

    return pd.DataFrame(results).sort_values(
        "today_score", ascending=False)


if __name__ == "__main__":
    conn  = sqlite3.connect(
        "data/silver/observatory_weather.db")
    names = pd.read_sql(
        "SELECT name FROM observatories LIMIT 3",
        conn)["name"].tolist()
    conn.close()

    print(f"\n Comparing: {names}\n")
    df = compare_sites(names)
    for _, row in df.iterrows():
        print(f"  {row['observatory']}")
        print(f"    Today   : {row['today_score']}/100")
        print(f"    Avg     : {row['avg_score']}/100")
        print(f"    Seeing  : {row['seeing_arcsec']}\"")
        print(f"    PWV     : {row['pwv_mm']} mm\n")