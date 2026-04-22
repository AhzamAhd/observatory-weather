import requests
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_observatories():
    path = "data/observatory_list.json"
    if not os.path.exists(path):
        print("  [ERROR] data/observatory_list.json not found.")
        print("  Run build_observatory_list.py first.")
        return []
    with open(path, "r") as f:
        return json.load(f)

def fetch_weather(observatory):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": observatory["latitude"],
        "longitude": observatory["longitude"],
        "current": [
            "cloudcover",
            "relativehumidity_2m",
            "windspeed_10m",
            "temperature_2m",
            "precipitation"
        ],
        "wind_speed_unit": "ms"
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        current = response.json()["current"]
        return {
            "observatory_name": observatory["name"],
            "country": observatory.get("country", "Unknown"),
            "latitude": observatory["latitude"],
            "longitude": observatory["longitude"],
            "altitude_m": observatory.get("altitude_m", 0),
            "mpc_code": observatory.get("code", ""),
            "cloud_cover_pct": current.get("cloudcover"),
            "humidity_pct": current.get("relativehumidity_2m"),
            "wind_speed_ms": current.get("windspeed_10m"),
            "temperature_c": current.get("temperature_2m"),
            "precipitation_mm": current.get("precipitation")
        }
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {observatory['name']}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR]   {observatory['name']} — {e}")
        return None

def fetch_all_parallel(observatories, max_workers=20):
    results = []
    failed  = 0
    print(f"  Fetching {len(observatories)} observatories in parallel ({max_workers} threads)...\n")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_obs = {executor.submit(fetch_weather, obs): obs for obs in observatories}
        completed = 0
        for future in as_completed(future_to_obs):
            completed += 1
            result = future.result()
            if result:
                results.append(result)
                print(f"  [{completed:02d}/{len(observatories)}] {result['observatory_name'][:50]:<50} cloud={result['cloud_cover_pct']}%")
            else:
                failed += 1
    return results, failed

def main():
    print(f"\n Starting parallel fetch — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")
    observatories = load_observatories()
    if not observatories:
        return
    print(f"  Loaded {len(observatories)} observatories\n")
    results, failed = fetch_all_parallel(observatories, max_workers=20)
    print(f"\n  Fetch complete — {len(results)} succeeded, {failed} failed\n")
    os.makedirs("data/bronze", exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"data/bronze/raw_weather_{date_str}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved {len(results)} records → {filename}\n")

if __name__ == "__main__":
    main()