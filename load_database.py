import os
import json
import glob
from datetime import datetime, timezone
from db import execute, fetch_one, query_df
from dotenv import load_dotenv

load_dotenv()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def calculate_score(cloud, humidity, wind):
    return round(max(0, min(100,
        100
        - ((cloud  or 0) * 0.50)
        - (max(0, (humidity or 0) - 85) * 2.0)
        - (max(0, (wind    or 0) - 15) * 2.0)
    )), 1)

def load_bronze_data():
    bronze_dir = "data/bronze"
    if not os.path.exists(bronze_dir):
        print(f"  [ERROR] Bronze dir not found")
        return []

    files = glob.glob(f"{bronze_dir}/*.json")
    if not files:
        print("  [ERROR] No bronze JSON files found")
        return []

    all_data = []
    for f in files:
        try:
            with open(f, "r") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    all_data.extend(data)
                else:
                    all_data.append(data)
        except Exception as e:
            print(f"  [WARN] Could not read {f}: {e}")

    print(f"  Loaded {len(all_data)} records from bronze")
    return all_data

# ── Build coordinate lookup cache ─────────────────────────────────
_coord_cache = {}

def get_obs_by_coords(lat, lon):
    """
    Find observatory ID by matching coordinates.
    Cached for performance.
    """
    key = (round(float(lat), 3), round(float(lon), 3))
    if key in _coord_cache:
        return _coord_cache[key]

    obs = fetch_one("""
        SELECT id, name FROM observatories
        WHERE ROUND(latitude::numeric, 3)  = %s
        AND   ROUND(longitude::numeric, 3) = %s
        LIMIT 1
    """, [key[0], key[1]])

    _coord_cache[key] = obs
    return obs

def build_coord_cache():
    """
    Pre-load all observatory coordinates into cache.
    Much faster than individual lookups.
    """
    print("  Building coordinate cache...")
    all_obs = query_df(
        "SELECT id, name, latitude, longitude "
        "FROM observatories"
    )
    for _, row in all_obs.iterrows():
        key = (
            round(float(row["latitude"]),  3),
            round(float(row["longitude"]), 3)
        )
        _coord_cache[key] = {
            "id":   row["id"],
            "name": row["name"]
        }
    print(f"  Cache built: {len(_coord_cache)} entries")

def upsert_weather_readings(data, now):
    """
    Upsert into weather_readings.
    Keeps latest reading per observatory per day.
    """
    fetch_date     = now.strftime("%Y-%m-%d")
    fetch_time     = now.strftime("%H:%M UTC")
    fetch_datetime = now.strftime("%Y-%m-%d %H:%M UTC")
    upserted       = 0
    not_found      = 0

    for record in data:
        try:
            lat = record.get("latitude")
            lon = record.get("longitude")
            if lat is None or lon is None:
                continue

            obs = get_obs_by_coords(lat, lon)
            if not obs:
                not_found += 1
                continue

            obs_id = obs["id"]
            cloud  = record.get("cloud_cover_pct") or 0
            humid  = record.get("humidity_pct")    or 0
            wind   = record.get("wind_speed_ms")   or 0
            score  = calculate_score(cloud, humid, wind)

            execute("""
                INSERT INTO weather_readings (
                    observatory_id,   fetch_date,
                    fetch_time,       fetch_datetime,
                    cloud_cover_pct,  humidity_pct,
                    wind_speed_ms,    temperature_c,
                    precipitation_mm, surface_pressure,
                    jet_stream_ms,    dewpoint_c,
                    observation_score
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (observatory_id, fetch_date)
                DO UPDATE SET
                    fetch_time        = EXCLUDED.fetch_time,
                    fetch_datetime    = EXCLUDED.fetch_datetime,
                    cloud_cover_pct   = EXCLUDED.cloud_cover_pct,
                    humidity_pct      = EXCLUDED.humidity_pct,
                    wind_speed_ms     = EXCLUDED.wind_speed_ms,
                    temperature_c     = EXCLUDED.temperature_c,
                    precipitation_mm  = EXCLUDED.precipitation_mm,
                    surface_pressure  = EXCLUDED.surface_pressure,
                    jet_stream_ms     = EXCLUDED.jet_stream_ms,
                    dewpoint_c        = EXCLUDED.dewpoint_c,
                    observation_score = EXCLUDED.observation_score
            """, [
                obs_id,        fetch_date,
                fetch_time,    fetch_datetime,
                cloud,         humid,
                wind,          record.get("temperature_c"),
                record.get("precipitation_mm"),
                record.get("surface_pressure"),
                record.get("jet_stream_ms"),
                record.get("dewpoint_c"),
                score
            ])
            upserted += 1

        except Exception as e:
            print(f"  [WARN] weather_readings: {e}")
            continue

    print(f"  weather_readings — "
          f"{upserted} upserted, "
          f"{not_found} not found in DB")

def insert_weather_history(data, now):
    """
    Insert daily snapshot into weather_history.
    One row per observatory per day — never overwrites.
    """
    fetch_date = now.strftime("%Y-%m-%d")
    inserted   = 0
    skipped    = 0
    not_found  = 0

    for record in data:
        try:
            lat = record.get("latitude")
            lon = record.get("longitude")
            if lat is None or lon is None:
                continue

            obs = get_obs_by_coords(lat, lon)
            if not obs:
                not_found += 1
                continue

            obs_id = obs["id"]
            cloud  = record.get("cloud_cover_pct") or 0
            humid  = record.get("humidity_pct")    or 0
            wind   = record.get("wind_speed_ms")   or 0
            score  = calculate_score(cloud, humid, wind)

            execute("""
                INSERT INTO weather_history (
                    observatory_id,   fetch_date,
                    cloud_cover_pct,  humidity_pct,
                    wind_speed_ms,    temperature_c,
                    precipitation_mm, surface_pressure,
                    jet_stream_ms,    dewpoint_c,
                    observation_score
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (observatory_id, fetch_date)
                DO NOTHING
            """, [
                obs_id,       fetch_date,
                cloud,        humid,
                wind,         record.get("temperature_c"),
                record.get("precipitation_mm"),
                record.get("surface_pressure"),
                record.get("jet_stream_ms"),
                record.get("dewpoint_c"),
                score
            ])
            inserted += 1

        except Exception as e:
            print(f"  [WARN] weather_history: {e}")
            continue

    print(f"  weather_history  — "
          f"{inserted} inserted, "
          f"{skipped} skipped, "
          f"{not_found} not found")

def print_summary():
    readings = fetch_one(
        "SELECT COUNT(*) AS c FROM weather_readings")
    history  = fetch_one(
        "SELECT COUNT(*) AS c FROM weather_history")
    obs      = fetch_one(
        "SELECT COUNT(*) AS c FROM observatories")
    dates    = fetch_one("""
        SELECT
            MIN(fetch_date) AS first_date,
            MAX(fetch_date) AS last_date,
            COUNT(DISTINCT fetch_date) AS days
        FROM weather_history
    """)

    print(f"\n  ── Database Summary ──────────────────")
    print(f"  Observatories:    {obs['c']}")
    print(f"  weather_readings: {readings['c']} rows")
    print(f"  weather_history:  {history['c']} rows")
    if dates and dates["days"]:
        print(f"  History range:    "
              f"{dates['first_date']} → "
              f"{dates['last_date']} "
              f"({dates['days']} days)")
    print(f"  ─────────────────────────────────────\n")

def main():
    now = utcnow()
    print(f"\n  Loading database — "
          f"{now.strftime('%Y-%m-%d %H:%M UTC')}\n")

    data = load_bronze_data()
    if not data:
        print("  [ERROR] No data to load")
        return

    # Build coordinate cache once
    build_coord_cache()

    # Upsert all into weather_readings
    print("\n  Upserting weather_readings...")
    upsert_weather_readings(data, now)

    # Insert daily snapshot into weather_history
    print("\n  Inserting weather_history...")
    insert_weather_history(data, now)

    print_summary()

if __name__ == "__main__":
    main()