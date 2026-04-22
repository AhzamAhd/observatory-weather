import sqlite3
import json
import os
from datetime import datetime

def get_connection():
    os.makedirs("data/silver", exist_ok=True)
    conn = sqlite3.connect("data/silver/observatory_weather.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS observatories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            country    TEXT,
            latitude   REAL,
            longitude  REAL,
            altitude_m INTEGER,
            mpc_code   TEXT,
            UNIQUE(name)
        );

        CREATE TABLE IF NOT EXISTS weather_readings (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            observatory_id   INTEGER REFERENCES observatories(id),
            fetch_date       TEXT,
            fetch_time       TEXT,
            fetch_datetime   TEXT,
            cloud_cover_pct  REAL,
            humidity_pct     REAL,
            wind_speed_ms    REAL,
            temperature_c    REAL,
            precipitation_mm REAL,
            surface_pressure REAL,
            dewpoint_c       REAL,
            wind_speed_80m   REAL,
            wind_speed_120m  REAL,
            jet_stream_ms    REAL,
            temp_500hpa      REAL,
            temp_850hpa      REAL,
            rh_1000hpa       REAL,
            rh_700hpa        REAL,
            rh_500hpa        REAL,
            rh_300hpa        REAL,
            UNIQUE(observatory_id, fetch_date)
        );
    """)
    conn.commit()
    print("  Tables ready.")

def insert_observatory(conn, record):
    conn.execute("""
        INSERT OR IGNORE INTO observatories
            (name, country, latitude, longitude, altitude_m, mpc_code)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        record["observatory_name"],
        record.get("country", "Unknown"),
        record["latitude"],
        record["longitude"],
        record.get("altitude_m", 0),
        record.get("mpc_code", "")
    ))
    conn.commit()
    row = conn.execute(
        "SELECT id FROM observatories WHERE name = ?",
        (record["observatory_name"],)
    ).fetchone()
    return row[0]

def insert_reading(conn, observatory_id, record):
    now            = datetime.utcnow()
    fetch_date     = now.strftime("%Y-%m-%d")
    fetch_time     = now.strftime("%H:%M UTC")
    fetch_datetime = now.strftime("%Y-%m-%d %H:%M UTC")

    conn.execute(
        "DELETE FROM weather_readings "
        "WHERE observatory_id = ? AND fetch_date = ?",
        (observatory_id, fetch_date)
    )
    conn.execute("""
        INSERT INTO weather_readings (
            observatory_id, fetch_date, fetch_time, fetch_datetime,
            cloud_cover_pct, humidity_pct, wind_speed_ms,
            temperature_c, precipitation_mm, surface_pressure,
            dewpoint_c, wind_speed_80m, wind_speed_120m,
            jet_stream_ms, temp_500hpa, temp_850hpa,
            rh_1000hpa, rh_700hpa, rh_500hpa, rh_300hpa
        ) VALUES (
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?
        )
    """, (
        observatory_id, fetch_date, fetch_time, fetch_datetime,
        record.get("cloud_cover_pct"),
        record.get("humidity_pct"),
        record.get("wind_speed_ms"),
        record.get("temperature_c"),
        record.get("precipitation_mm"),
        record.get("surface_pressure"),
        record.get("dewpoint_c"),
        record.get("wind_speed_80m"),
        record.get("wind_speed_120m"),
        record.get("jet_stream_ms"),
        record.get("temp_500hpa"),
        record.get("temp_850hpa"),
        record.get("rh_1000hpa"),
        record.get("rh_700hpa"),
        record.get("rh_500hpa"),
        record.get("rh_300hpa"),
    ))
    conn.commit()

def main():
    print(
        f"\n Loading into SQLite — "
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

    conn = get_connection()
    create_tables(conn)

    for record in records:
        obs_id = insert_observatory(conn, record)
        insert_reading(conn, obs_id, record)
        print(f"  Loaded → {record['observatory_name']}")

    conn.close()
    print(f"\n Done. {len(records)} records loaded.\n")

if __name__ == "__main__":
    main()