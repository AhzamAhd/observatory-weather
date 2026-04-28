import requests
from bs4 import BeautifulSoup
import json
import os
import math

def fetch_mpc_observatories():
    print("\n Fetching observatory list from MPC...\n")
    url = "https://www.minorplanetcenter.net/iau/lists/ObsCodesF.html"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] Could not fetch MPC list: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    pre  = soup.find("pre")
    if not pre:
        print("  [ERROR] Could not find data in page")
        return []

    lines         = pre.text.strip().split("\n")
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
            lat     = math.degrees(
                math.atan2(sin_phi, cos_phi))

            if lon > 180:
                lon = lon - 360
            if abs(lat) > 90 or abs(lon) > 180:
                continue
            if cos_phi == 0 and sin_phi == 0:
                continue
            if len(name) < 3:
                continue

            # Skip roving observers and spacecraft
            skip_keywords = [
                "Roving", "spacecraft", "Geocenter",
                "Satellite", "HST", "Hubble",
                "WISE", "Spitzer", "Kepler",
                "TESS", "spacecraft", "Great Circle"
            ]
            if any(kw.lower() in name.lower()
                   for kw in skip_keywords):
                continue

            observatories.append({
                "code":      code,
                "name":      name,
                "latitude":  round(lat, 4),
                "longitude": round(lon, 4),
                "altitude_m": 0,
                "country":   "Unknown"
            })

        except (ValueError, IndexError):
            continue

    print(
        f"  Found {len(observatories)} valid "
        f"observatories in MPC database"
    )
    return observatories

def assign_country(lat, lon):
    """
    Rough country assignment based on coordinates.
    Good enough for display purposes.
    """
    if -90 <= lat <= -60:
        return "Antarctica"
    if 24 <= lat <= 50 and -125 <= lon <= -66:
        return "USA"
    if 49 <= lat <= 83 and -141 <= lon <= -52:
        return "Canada"
    if 14 <= lat <= 33 and -118 <= lon <= -86:
        return "Mexico"
    if -55 <= lat <= -20 and -75 <= lon <= -35:
        return "Argentina"
    if -33 <= lat <= 5 and -73 <= lon <= -35:
        return "Brazil"
    if -56 <= lat <= -17 and -75 <= lon <= -66:
        return "Chile"
    if 36 <= lat <= 71 and -10 <= lon <= 35:
        return "Europe"
    if 50 <= lat <= 61 and -8 <= lon <= 2:
        return "UK"
    if 41 <= lat <= 51 and -5 <= lon <= 10:
        return "France"
    if 47 <= lat <= 55 and 6 <= lon <= 15:
        return "Germany"
    if 36 <= lat <= 47 and 7 <= lon <= 19:
        return "Italy"
    if 36 <= lat <= 44 and -9 <= lon <= 4:
        return "Spain"
    if 55 <= lat <= 70 and 14 <= lon <= 32:
        return "Scandinavia"
    if 20 <= lat <= 55 and 35 <= lon <= 145:
        return "Asia"
    if 20 <= lat <= 55 and 73 <= lon <= 135:
        return "China"
    if 8 <= lat <= 37 and 68 <= lon <= 97:
        return "India"
    if 30 <= lat <= 46 and 129 <= lon <= 146:
        return "Japan"
    if -45 <= lat <= -10 and 113 <= lon <= 154:
        return "Australia"
    if -47 <= lat <= -34 and 166 <= lon <= 178:
        return "New Zealand"
    if -5 <= lat <= 38 and -18 <= lon <= 55:
        return "Africa"
    if 15 <= lat <= 42 and -18 <= lon <= 60:
        return "Middle East"
    if 18 <= lat <= 23 and -160 <= lon <= -154:
        return "Hawaii, USA"
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return "Unknown"
    return "Unknown"

def assign_telescope_type(name, lat):
    """
    Guess telescope type from observatory name.
    """
    name_lower = name.lower()

    radio_keywords = [
        "radio", "vlbi", "vla", "alma", "parkes",
        "jodrell", "effelsberg", "arecibo", "lovell",
        "meerkat", "ska", "lofar", "fast", "millimeter",
        "submillimeter", "microwave", "pulsar"
    ]
    infrared_keywords = [
        "infrared", "irtf", "ukirt", "vista",
        "spitzer", "wise", "iras", "sofia"
    ]
    solar_keywords = [
        "solar", "sun", "helio", "coronagraph",
        "sunspot", "chromospheric"
    ]
    space_keywords = [
        "space", "satellite", "orbital", "hubble",
        "kepler", "tess", "cheops", "jwst"
    ]

    if any(kw in name_lower for kw in radio_keywords):
        return "radio"
    if any(kw in name_lower for kw in infrared_keywords):
        return "infrared"
    if any(kw in name_lower for kw in solar_keywords):
        return "solar"
    if any(kw in name_lower for kw in space_keywords):
        return "space"
    return "optical"

def remove_duplicates(observatories):
    """
    Remove observatories that are too close together
    (within 0.1 degrees) to avoid redundant data fetches.
    """
    print("  Removing duplicates...")
    unique   = []
    seen_pos = []

    for obs in observatories:
        too_close = False
        for lat, lon in seen_pos:
            if (abs(obs["latitude"] - lat) < 0.05 and
                    abs(obs["longitude"] - lon) < 0.05):
                too_close = True
                break
        if not too_close:
            unique.append(obs)
            seen_pos.append(
                (obs["latitude"], obs["longitude"]))

    print(
        f"  Removed {len(observatories) - len(unique)} "
        f"duplicates"
    )
    return unique

def save_list(observatories):
    os.makedirs("data", exist_ok=True)
    path = "data/observatory_list.json"
    with open(path, "w") as f:
        json.dump(observatories, f, indent=2)
    print(f"\n  Saved {len(observatories)} "
          f"observatories → {path}\n")

def main():
    all_obs = fetch_mpc_observatories()
    if not all_obs:
        return

    # Assign country and telescope type
    print("  Assigning countries and telescope types...")
    for obs in all_obs:
        obs["country"]       = assign_country(
            obs["latitude"], obs["longitude"])
        obs["telescope_type"] = assign_telescope_type(
            obs["name"], obs["latitude"])

    # Remove duplicates
    all_obs = remove_duplicates(all_obs)

    # Print breakdown by type
    types = {}
    for obs in all_obs:
        t = obs["telescope_type"]
        types[t] = types.get(t, 0) + 1

    print("\n  Telescope type breakdown:")
    for t, count in sorted(
        types.items(), key=lambda x: -x[1]
    ):
        print(f"    {t:<15} — {count}")

    # Print breakdown by country
    countries = {}
    for obs in all_obs:
        c = obs["country"]
        countries[c] = countries.get(c, 0) + 1

    print("\n  Top 15 countries:")
    for c, count in sorted(
        countries.items(), key=lambda x: -x[1]
    )[:15]:
        print(f"    {c:<25} — {count}")

    print(f"\n  Total: {len(all_obs)} observatories")

    save_list(all_obs)

    print("  Sample:")
    for o in all_obs[:5]:
        print(
            f"    {o['code']} — {o['name']} "
            f"({o['country']}) [{o['telescope_type']}]"
        )

if __name__ == "__main__":
    main()