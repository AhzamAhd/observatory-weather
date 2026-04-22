import sqlite3
import pandas as pd
import os
from datetime import datetime

def get_connection():
    return sqlite3.connect("data/silver/observatory_weather.db")

def create_scoring_view(conn):
    conn.executescript("""
        DROP VIEW IF EXISTS observation_quality;
        CREATE VIEW observation_quality AS
        SELECT
            o.name         AS observatory,
            o.country,
            o.altitude_m,
            o.mpc_code,
            w.fetch_date,
            w.fetch_time,
            w.fetch_datetime,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS observation_score,
            CASE
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 80 THEN 'Excellent'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 60 THEN 'Good'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 40 THEN 'Marginal'
                ELSE 'Poor'
            END AS condition
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id;
    """)
    conn.commit()
    print("  Scoring view created.")

def show_scores(conn):
    df = pd.read_sql("""
        SELECT observatory, country, altitude_m, mpc_code,
               fetch_date, fetch_time, cloud_cover_pct,
               humidity_pct, wind_speed_ms, temperature_c,
               observation_score, condition
        FROM observation_quality
        ORDER BY observation_score DESC
    """, conn)
    print("\n  ── Observation Quality Scores ──\n")
    for _, row in df.iterrows():
        print(f"  {row['observatory']}")
        print(f"    Score  : {row['observation_score']} / 100  [{row['condition']}]")
        print(f"    Fetched: {row['fetch_date']} at {row['fetch_time']}")
        print(f"    Cloud  : {row['cloud_cover_pct']}%  "
              f"Humidity: {row['humidity_pct']}%  "
              f"Wind: {row['wind_speed_ms']} m/s\n")
    os.makedirs("data/gold", exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    csv_path = f"data/gold/observation_scores_{date_str}.csv"
    df.to_csv(csv_path, index=False)
    print(f"  Saved → {csv_path}\n")
    return df

def main():
    print(f"\n Scoring — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")
    conn = get_connection()
    create_scoring_view(conn)
    show_scores(conn)
    conn.close()

if __name__ == "__main__":
    main()