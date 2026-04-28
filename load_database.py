import json
import os
from datetime import datetime
from db import get_connection, execute_many

def insert_observatories_and_readings(records):
    """
    Insert observatories and weather readings
    in bulk into Supabase.
    """
    conn = get_connection()
    cur  = conn.cursor()

    # ── Step 1: Upsert observatories ──────────────────────
    print("  Upserting observatories...")
    obs_rows = [
        (
            r["observatory_name"],
            r.get("country", "Unknown"),
            r["latitude"],
            r["longitude"],
            r.get("altitude_m", 0),
            r.get("mpc_code", "")
        )
        for r in records
    ]

    import psycopg2.extras
    psycopg2.extras.execute_values(cur, """
        INSERT INTO observatories
            (name, country, latitude, longitude,
             altitude_m, mpc_code)
        VALUES %s
        ON CONFLICT (name) DO UPDATE SET
            country    = EXCLUDED.country,
            latitude   = EXCLUDED.latitude,
            longitude  = EXCLUDED.longitude,
            altitude_m = EXCLUDED.altitude_m,
            mpc_code   = EXCLUDED.mpc_code
    """, obs_rows)
    conn.commit()
    print(f"  ✅ {len(obs_rows)} observatories")

    # ── Step 2: Get name → id mapping ─────────────────────
    cur.execute(
        "SELECT id, name FROM observatories")
    name_to_id = {n: i for i, n in cur.fetchall()}

    # ── Step 3: Insert weather readings ───────────────────
    print("  Inserting weather readings...")
    now            = datetime.utcnow()
    fetch_date     = now.strftime("%Y-%m-%d")
    fetch_time     = now.strftime("%H:%M UTC")
    fetch_datetime = now.strftime("%Y-%m-%d %H:%M UTC")     

    weather_rows = []
    for r in records:
        obs_id = name_to_id.get(r["observatory_name"])
        if not obs_id:
            continue
        weather_rows.append((
            obs_id, fetch_date, fetch_time,
            fetch_datetime,
            r.get("cloud_cover_pct"),
            r.get("humidity_pct"),
            r.get("wind_speed_ms"),
            r.get("temperature_c"),
            r.get("precipitation_mm"),
            r.get("surface_pressure"),
            r.get("dewpoint_c"),
            r.get("wind_speed_80m"),
            r.get("wind_speed_120m"),
            r.get("jet_stream_ms"),
            r.get("temp_500hpa"),
            r.get("temp_850hpa"),
            r.get("rh_1000hpa"),
            r.get("rh_700hpa"),
            r.get("rh_500hpa"),
            r.get("rh_300hpa"),
        ))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO weather_readings (
            observatory_id, fetch_date, fetch_time,
            fetch_datetime, cloud_cover_pct, humidity_pct,
            wind_speed_ms, temperature_c, precipitation_mm,
            surface_pressure, dewpoint_c, wind_speed_80m,
            wind_speed_120m, jet_stream_ms,
            temp_500hpa, temp_850hpa,
            rh_1000hpa, rh_700hpa, rh_500hpa, rh_300hpa
        ) VALUES %s
        ON CONFLICT (observatory_id, fetch_date)
        DO UPDATE SET
            fetch_time       = EXCLUDED.fetch_time,
            fetch_datetime   = EXCLUDED.fetch_datetime,
            cloud_cover_pct  = EXCLUDED.cloud_cover_pct,
            humidity_pct     = EXCLUDED.humidity_pct,
            wind_speed_ms    = EXCLUDED.wind_speed_ms,
            temperature_c    = EXCLUDED.temperature_c,
            precipitation_mm = EXCLUDED.precipitation_mm,
            surface_pressure = EXCLUDED.surface_pressure,
            dewpoint_c       = EXCLUDED.dewpoint_c,
            wind_speed_80m   = EXCLUDED.wind_speed_80m,
            wind_speed_120m  = EXCLUDED.wind_speed_120m,
            jet_stream_ms    = EXCLUDED.jet_stream_ms,
            temp_500hpa      = EXCLUDED.temp_500hpa,
            temp_850hpa      = EXCLUDED.temp_850hpa,
            rh_1000hpa       = EXCLUDED.rh_1000hpa,
            rh_700hpa        = EXCLUDED.rh_700hpa,
            rh_500hpa        = EXCLUDED.rh_500hpa,
            rh_300hpa        = EXCLUDED.rh_300hpa
    """, weather_rows)
    conn.commit()
    print(f"  ✅ {len(weather_rows)} weather readings")

    cur.close()
    conn.close()

def main():
    print(
        f"\n Loading into Supabase — "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
    )
    date_str    = datetime.utcnow().strftime("%Y-%m-%d")
    bronze_file = f"data/bronze/raw_weather_{date_str}.json"

    if not os.path.exists(bronze_file):
        print(f"  [ERROR] File not found: {bronze_file}")
        return

    with open(bronze_file, "r") as f:
        records = json.load(f)

    print(f"  Found {len(records)} records")
    insert_observatories_and_readings(records)
    print(f"\n ✅ Done. {len(records)} records loaded.\n")

if __name__ == "__main__":
    main()