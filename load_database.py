import sqlite3
import json
import os
from datetime import datetime

# ── Connect to (or create) the database ──────────────────────────
def get_connection():
    os.makedirs("data/silver", exist_ok=True)
    conn = sqlite3.connect("data/silver/observatory_weather.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ── Create tables if they don't exist ────────────────────────────
def create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS observatories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            country     TEXT,
            latitude    REAL,
            longitude   REAL,
            altitude_m  INTEGER,
            UNIQUE(name)
        );

        CREATE TABLE IF NOT EXISTS weather_readings (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            observatory_id      INTEGER REFERENCES observatories(id),
            timestamp_utc       TEXT,
            cloud_cover_pct     REAL,
            humidity_pct        REAL,
            wind_speed_ms       REAL,
            temperature_c       REAL,
            precipitation_mm    REAL,
            UNIQUE(observatory_id, timestamp_utc)
        );
    """)
    conn.commit()
    print("  Tables ready.")

# ── Insert one observatory (skip if already exists) ───────────────
def insert_observatory(conn, record):
    conn.execute("""
        INSERT OR IGNORE INTO observatories
            (name, country, latitude, longitude, altitude_m)
        VALUES (?, ?, ?, ?, ?)
    """, (
        record["observatory_name"],
        record["country"],
        record["latitude"],
        record["longitude"],
        record["altitude_m"]
    ))
    conn.commit()

    row = conn.execute(
        "SELECT id FROM observatories WHERE name = ?",
        (record["observatory_name"],)
    ).fetchone()

    return row[0]

# ── Insert one weather reading (skip if duplicate) ────────────────
def insert_reading(conn, observatory_id, record):
    conn.execute("""
        INSERT OR IGNORE INTO weather_readings
            (observatory_id, timestamp_utc, cloud_cover_pct,
             humidity_pct, wind_speed_ms, temperature_c, precipitation_mm)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        observatory_id,
        record["timestamp_utc"],
        record["cloud_cover_pct"],
        record["humidity_pct"],
        record["wind_speed_ms"],
        record["temperature_c"],
        record["precipitation_mm"]
    ))
    conn.commit()

# ── Main runner ───────────────────────────────────────────────────
def main():
    print(f"\n Loading data into SQLite — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")

    # Find today's bronze file
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    bronze_file = f"data/bronze/raw_weather_{date_str}.json"

    if not os.path.exists(bronze_file):
        print(f"  [ERROR] Bronze file not found: {bronze_file}")
        print("  Run fetch_weather.py first.")
        return

    # Load the JSON
    with open(bronze_file, "r") as f:
        records = json.load(f)

    print(f"  Found {len(records)} records in {bronze_file}")

    # Connect and set up tables
    conn = get_connection()
    create_tables(conn)

    # Insert each record
    inserted = 0
    for record in records:
        obs_id = insert_observatory(conn, record)
        insert_reading(conn, obs_id, record)
        inserted += 1
        print(f"  Loaded → {record['observatory_name']}")

    conn.close()
    print(f"\n Done. {inserted} records loaded into data/silver/observatory_weather.db\n")


if __name__ == "__main__":
    main()