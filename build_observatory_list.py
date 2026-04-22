import requests
from bs4 import BeautifulSoup
import json
import os
import math

def fetch_mpc_observatories():
    print("\n Fetching observatory list from MPC...\n")
    url = "https://www.minorplanetcenter.net/iau/lists/ObsCodesF.html"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] Could not fetch MPC list: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    pre = soup.find("pre")
    if not pre:
        print("  [ERROR] Could not find data in page")
        return []

    lines = pre.text.strip().split("\n")
    observatories = []

    for line in lines[2:]:
        try:
            if len(line) < 30:
                continue
            code    = line[0:3].strip()
            lon_str = line[4:13].strip()
            cos_str = line[13:21].strip()
            sin_str = line[21:30].strip()
            name    = line[30:].strip()

            if not lon_str or not cos_str or not sin_str or not name:
                continue

            lon     = float(lon_str)
            cos_phi = float(cos_str)
            sin_phi = float(sin_str)
            lat     = math.degrees(math.atan2(sin_phi, cos_phi))

            if lon > 180:
                lon = lon - 360
            if abs(lat) > 90 or abs(lon) > 180:
                continue
            if cos_phi == 0 and sin_phi == 0:
                continue

            observatories.append({
                "code": code,
                "name": name,
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "altitude_m": 0,
                "country": "Unknown"
            })
        except (ValueError, IndexError):
            continue

    print(f"  Found {len(observatories)} observatories in MPC database")
    return observatories

def select_100_diverse(observatories):
    regions = {
        "north_america": {"lat": (15, 75),  "lon": (-170, -50), "target": 20},
        "south_america": {"lat": (-60, 15), "lon": (-85, -30),  "target": 15},
        "europe":        {"lat": (35, 72),  "lon": (-15, 45),   "target": 20},
        "africa":        {"lat": (-40, 38), "lon": (-20, 55),   "target": 8},
        "asia":          {"lat": (0, 75),   "lon": (45, 145),   "target": 18},
        "oceania":       {"lat": (-50, 0),  "lon": (110, 180),  "target": 10},
        "pacific":       {"lat": (15, 25),  "lon": (-180, -145),"target": 5},
        "antarctica":    {"lat": (-90, -60),"lon": (-180, 180), "target": 4},
    }

    selected = []
    used_names = set()

    for region, bounds in regions.items():
        candidates = [
            o for o in observatories
            if bounds["lat"][0] <= o["latitude"] <= bounds["lat"][1]
            and bounds["lon"][0] <= o["longitude"] <= bounds["lon"][1]
            and o["name"] not in used_names
            and len(o["name"]) > 3
        ]
        step   = max(1, len(candidates) // bounds["target"])
        picked = candidates[::step][:bounds["target"]]
        for obs in picked:
            used_names.add(obs["name"])
            selected.append(obs)
        print(f"  {region:<20} — {len(picked)} selected from {len(candidates)} candidates")

    print(f"\n  Total selected: {len(selected)}")
    return selected[:100]

def save_list(observatories):
    os.makedirs("data", exist_ok=True)
    path = "data/observatory_list.json"
    with open(path, "w") as f:
        json.dump(observatories, f, indent=2)
    print(f"\n  Saved → {path}\n")

def main():
    all_obs  = fetch_mpc_observatories()
    if not all_obs:
        return
    selected = select_100_diverse(all_obs)
    save_list(selected)
    print("  Sample of selected observatories:")
    for o in selected[:10]:
        print(f"    {o['code']} — {o['name']} ({o['latitude']}, {o['longitude']})")

if __name__ == "__main__":
    main()