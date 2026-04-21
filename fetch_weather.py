import requests
import json
import os
from datetime import datetime

# ── Observatory list ──────────────────────────────────────────────
OBSERVATORIES = [
    {
        "name": "Mauna Kea Observatory",
        "country": "USA",
        "latitude": 19.8207,
        "longitude": -155.4681,
        "altitude_m": 4205
    },
    {
        "name": "Paranal Observatory",
        "country": "Chile",
        "latitude": -24.6275,
        "longitude": -70.4044,
        "altitude_m": 2635
    },
    {
        "name": "La Palma Observatory",
        "country": "Spain",
        "latitude": 28.7606,
        "longitude": -17.8795,
        "altitude_m": 2396
    },
    {
        "name": "Cerro Pachon Observatory",
        "country": "Chile",
        "latitude": -30.2407,
        "longitude": -70.7366,
        "altitude_m": 2722
    },
    {
        "name": "Himalayan Chandra Telescope",
        "country": "India",
        "latitude": 32.7794,
        "longitude": 78.9627,
        "altitude_m": 4500
    }
]

# ── Fetch function ────────────────────────────────────────────────
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
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data["current"]

        return {
            "observatory_name": observatory["name"],
            "country": observatory["country"],
            "latitude": observatory["latitude"],
            "longitude": observatory["longitude"],
            "altitude_m": observatory["altitude_m"],
            "timestamp_utc": datetime.utcnow().isoformat(),
            "cloud_cover_pct": current.get("cloudcover"),
            "humidity_pct": current.get("relativehumidity_2m"),
            "wind_speed_ms": current.get("windspeed_10m"),
            "temperature_c": current.get("temperature_2m"),
            "precipitation_mm": current.get("precipitation")
        }

    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT]  {observatory['name']} took too long — skipping")
        return None

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR]    {observatory['name']} failed: {e}")
        return None


# ── Main runner ───────────────────────────────────────────────────
def main():
    print(f"\n Starting weather fetch — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")

    results = []

    for obs in OBSERVATORIES:
        print(f"  Fetching → {obs['name']}...")
        record = fetch_weather(obs)

        if record:
            results.append(record)
            print(f"  Done      cloud={record['cloud_cover_pct']}%  "
                  f"humidity={record['humidity_pct']}%  "
                  f"wind={record['wind_speed_ms']} m/s")

    # ── Save to Bronze layer JSON ─────────────────────────────────
    os.makedirs("data/bronze", exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"data/bronze/raw_weather_{date_str}.json"

    with open(filename, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n Saved {len(results)} records → {filename}\n")


if __name__ == "__main__":
    main()