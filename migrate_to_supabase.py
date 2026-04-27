import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# ── Connection details ────────────────────────────────────────────
PG_HOST     = os.environ.get("SUPABASE_DB_HOST")
PG_PASSWORD = os.environ.get("SUPABASE_DB_PASSWORD")
PG_USER     = os.environ.get(
    "SUPABASE_DB_USER", "postgres")
PG_DB       = "postgres"
PG_PORT     = 5432

SQLITE_PATH = "data/silver/observatory_weather.db"

def get_pg_connection():
    return psycopg2.connect(
        host     = PG_HOST,
        port     = PG_PORT,
        database = PG_DB,
        user     = PG_USER,
        password = PG_PASSWORD,
        sslmode  = "require"
    )

def migrate_observatories():
    print("\n  Migrating observatories...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.execute("""
        SELECT name, country, latitude, longitude,
               altitude_m, mpc_code
        FROM observatories
    """)
    rows = [
        (r["name"], r["country"], r["latitude"],
         r["longitude"], r["altitude_m"], r["mpc_code"])
        for r in cursor.fetchall()
    ]
    sqlite_conn.close()

    pg_conn = get_pg_connection()
    pg_cur  = pg_conn.cursor()

    execute_values(pg_cur, """
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
    """, rows)

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()
    print(f"  ✅ Migrated {len(rows)} observatories")

def migrate_weather_readings():
    print("\n  Migrating weather readings...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # Build mapping of observatory names to PG ids
    pg_conn = get_pg_connection()
    pg_cur  = pg_conn.cursor()
    pg_cur.execute(
        "SELECT id, name FROM observatories")
    name_to_id = {n: i for i, n in pg_cur.fetchall()}
    pg_cur.close()

    # Get all weather readings with observatory names
    cursor = sqlite_conn.execute("""
        SELECT
            o.name AS obs_name,
            w.fetch_date, w.fetch_time, w.fetch_datetime,
            w.cloud_cover_pct, w.humidity_pct,
            w.wind_speed_ms, w.temperature_c,
            w.precipitation_mm, w.surface_pressure,
            w.dewpoint_c, w.wind_speed_80m,
            w.wind_speed_120m, w.jet_stream_ms,
            w.temp_500hpa, w.temp_850hpa,
            w.rh_1000hpa, w.rh_700hpa,
            w.rh_500hpa, w.rh_300hpa
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
    """)

    rows = []
    for r in cursor.fetchall():
        obs_id = name_to_id.get(r["obs_name"])
        if obs_id is None:
            continue
        rows.append((
            obs_id,
            r["fetch_date"], r["fetch_time"],
            r["fetch_datetime"],
            r["cloud_cover_pct"], r["humidity_pct"],
            r["wind_speed_ms"], r["temperature_c"],
            r["precipitation_mm"], r["surface_pressure"],
            r["dewpoint_c"], r["wind_speed_80m"],
            r["wind_speed_120m"], r["jet_stream_ms"],
            r["temp_500hpa"], r["temp_850hpa"],
            r["rh_1000hpa"], r["rh_700hpa"],
            r["rh_500hpa"], r["rh_300hpa"]
        ))
    sqlite_conn.close()

    pg_cur = pg_conn.cursor()
    execute_values(pg_cur, """
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
    """, rows)

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()
    print(f"  ✅ Migrated {len(rows)} weather readings")

def migrate_precomputed():
    print("\n  Migrating precomputed data...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)

    # Check if table exists
    table_exists = sqlite_conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='precomputed'
    """).fetchone()

    if not table_exists:
        print("  [SKIP] No precomputed table in SQLite")
        sqlite_conn.close()
        return

    cursor = sqlite_conn.execute(
        "SELECT key, value, computed_at FROM precomputed")
    rows = [
        (r[0], r[1], r[2])
        for r in cursor.fetchall()
    ]
    sqlite_conn.close()

    if not rows:
        print("  [SKIP] No precomputed data")
        return

    pg_conn = get_pg_connection()
    pg_cur  = pg_conn.cursor()

    for key, value, computed_at in rows:
        pg_cur.execute("""
            INSERT INTO precomputed
                (key, value, computed_at)
            VALUES (%s, %s::jsonb, %s)
            ON CONFLICT (key) DO UPDATE SET
                value       = EXCLUDED.value,
                computed_at = EXCLUDED.computed_at
        """, (key, value, computed_at))

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()
    print(f"  ✅ Migrated {len(rows)} precomputed entries")

def verify_migration():
    print("\n  Verifying migration...")
    pg_conn = get_pg_connection()
    pg_cur  = pg_conn.cursor()

    pg_cur.execute("SELECT COUNT(*) FROM observatories")
    obs_count = pg_cur.fetchone()[0]

    pg_cur.execute(
        "SELECT COUNT(*) FROM weather_readings")
    weather_count = pg_cur.fetchone()[0]

    pg_cur.execute("SELECT COUNT(*) FROM precomputed")
    precomp_count = pg_cur.fetchone()[0]

    pg_cur.close()
    pg_conn.close()

    print(f"\n  📊 Final counts in Supabase:")
    print(f"     Observatories:    {obs_count}")
    print(f"     Weather readings: {weather_count}")
    print(f"     Precomputed:      {precomp_count}")

def main():
    print("\n  🚀 Migrating SQLite → Supabase PostgreSQL")
    print("  " + "─" * 45)

    if not PG_HOST or not PG_PASSWORD:
        print("\n  ❌ Missing environment variables.")
        print("  Set SUPABASE_DB_HOST and "
              "SUPABASE_DB_PASSWORD in .env\n")
        return

    try:
        migrate_observatories()
        migrate_weather_readings()
        migrate_precomputed()
        verify_migration()
        print("\n  🎉 Migration complete!\n")
    except Exception as e:
        print(f"\n  ❌ Migration failed: {e}\n")

if __name__ == "__main__":
    main()