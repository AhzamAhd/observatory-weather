from dotenv import load_dotenv
load_dotenv()

import os
import requests
import math
from datetime import datetime, timedelta, timezone


# ── API key ───────────────────────────────────────────────────────
def get_nasa_key():
    """Get NASA API key from environment only."""
    key = os.environ.get("NASA_API_KEY")
    if key:
        return key
    return "DEMO_KEY"

NASA_API_KEY = get_nasa_key()
BASE_URL     = "https://api.nasa.gov/neo/rest/v1"


# ── Parse single asteroid ─────────────────────────────────────────
def parse_asteroid(neo, date_str):
    """Parse a single NEO object from NASA API."""
    try:
        name      = neo.get("name", "Unknown")
        neo_id    = neo.get("id", "")
        nasa_url  = neo.get("nasa_jpl_url", "")
        hazardous = neo.get(
            "is_potentially_hazardous_asteroid", False)
        magnitude = neo.get("absolute_magnitude_h", None)
        is_sentry = neo.get("is_sentry_object", False)

        # Diameter
        diam     = neo.get("estimated_diameter", {})
        diam_km  = diam.get("kilometers", {})
        diam_m   = diam.get("meters", {})
        diam_min = diam_km.get(
            "estimated_diameter_min", 0)
        diam_max = diam_km.get(
            "estimated_diameter_max", 0)
        diam_avg   = round((diam_min + diam_max) / 2, 4)
        diam_m_avg = round(
            (diam_m.get("estimated_diameter_min", 0) +
             diam_m.get("estimated_diameter_max", 0)) / 2,
            1)

        # Close approach
        approaches = neo.get("close_approach_data", [])
        if not approaches:
            return None

        approach      = approaches[0]
        miss_km       = float(approach.get(
            "miss_distance", {}).get("kilometers", 0))
        miss_lunar    = float(approach.get(
            "miss_distance", {}).get("lunar", 0))
        miss_au       = float(approach.get(
            "miss_distance", {}).get("astronomical", 0))
        velocity_km_s = float(approach.get(
            "relative_velocity", {}).get(
            "kilometers_per_second", 0))
        velocity_km_h = float(approach.get(
            "relative_velocity", {}).get(
            "kilometers_per_hour", 0))
        approach_date = approach.get(
            "close_approach_date", date_str)
        approach_time = approach.get(
            "close_approach_date_full", approach_date)
        orbiting_body = approach.get(
            "orbiting_body", "Earth")

        # Orbital data
        orbital     = neo.get("orbital_data", {})
        orbit_class = orbital.get(
            "orbit_class", {}).get(
            "orbit_class_type", "NEO")

        threat  = assess_threat(
            miss_km, diam_avg, hazardous)
        energy  = estimate_impact_energy(
            diam_avg, velocity_km_s)

        return {
            "name":               name,
            "id":                 neo_id,
            "nasa_url":           nasa_url,
            "hazardous":          hazardous,
            "is_sentry":          is_sentry,
            "magnitude":          magnitude,
            "diameter_km":        diam_avg,
            "diameter_m":         diam_m_avg,
            "diameter_min_km":    round(diam_min, 4),
            "diameter_max_km":    round(diam_max, 4),
            "miss_distance_km":   round(miss_km, 0),
            "miss_distance_lunar":round(miss_lunar, 2),
            "miss_distance_au":   round(miss_au, 6),
            "velocity_km_s":      round(velocity_km_s, 3),
            "velocity_km_h":      round(velocity_km_h, 0),
            "approach_date":      approach_date,
            "approach_time":      approach_time,
            "orbiting_body":      orbiting_body,
            "orbit_class":        orbit_class,
            "threat_level":       threat["level"],
            "threat_color":       threat["color"],
            "threat_desc":        threat["desc"],
            "size_class":         classify_size(diam_avg),
            "size_comparison":    size_comparison(diam_m_avg),
            "impact_energy":      energy,
            "date_str":           date_str,
        }

    except Exception as e:
        return None


# ── Assessment helpers ────────────────────────────────────────────
def assess_threat(miss_km, diam_km, hazardous):
    """Assess threat level."""
    lunar = 384400
    if miss_km < lunar * 0.5 and diam_km > 0.1:
        return {
            "level": "⚠️ Watch",
            "color": "#E74C3C",
            "desc":  "Very close approach within 0.5 LD"
        }
    if hazardous and miss_km < lunar * 2:
        return {
            "level": "🟡 Hazardous",
            "color": "#EF9F27",
            "desc":  "NASA PHA — close approach"
        }
    if hazardous:
        return {
            "level": "🟡 PHA",
            "color": "#F39C12",
            "desc":  "Potentially Hazardous Asteroid"
        }
    if miss_km < lunar * 2:
        return {
            "level": "🔵 Notable",
            "color": "#378ADD",
            "desc":  "Close approach within 2 LD"
        }
    return {
        "level": "🟢 Safe",
        "color": "#1D9E75",
        "desc":  "Safe passing distance"
    }


def classify_size(diam_km):
    """Classify asteroid by diameter."""
    if diam_km >= 1.0:     return "🔴 Large (>1km)"
    elif diam_km >= 0.14:  return "🟠 Medium (140m-1km)"
    elif diam_km >= 0.025: return "🟡 Small (25-140m)"
    else:                  return "🟢 Tiny (<25m)"


def size_comparison(diam_m):
    """Compare to familiar objects."""
    if diam_m < 5:      return "car-sized"
    elif diam_m < 20:   return "house-sized"
    elif diam_m < 50:   return "airplane-sized"
    elif diam_m < 100:  return "football pitch-sized"
    elif diam_m < 300:  return "skyscraper-sized"
    elif diam_m < 1000: return "mountain-sized"
    elif diam_m < 5000: return "city-sized"
    else:               return "continent-sized"


def estimate_impact_energy(diam_km, velocity_km_s):
    """Estimate impact energy in megatons TNT."""
    try:
        if diam_km <= 0 or velocity_km_s <= 0:
            return None
        density    = 2500
        radius_m   = (diam_km * 1000) / 2
        volume     = (4/3) * math.pi * radius_m**3
        mass       = density * volume
        velocity_m = velocity_km_s * 1000
        energy_j   = 0.5 * mass * velocity_m**2
        megatons   = energy_j / 4.184e15
        if megatons < 0.001:
            return f"{megatons*1000:.4f} kilotons TNT"
        elif megatons < 1:
            return f"{megatons:.3f} megatons TNT"
        elif megatons < 1000:
            return f"{megatons:.1f} megatons TNT"
        else:
            return f"{megatons/1000:.1f} gigatons TNT"
    except Exception:
        return None


def format_distance(km):
    """Format distance in human readable form."""
    lunar = 384400
    if km < lunar:
        return f"{km:,.0f} km ({km/lunar:.2f} LD)"
    else:
        return f"{km/lunar:.1f} LD ({km/149597870:.4f} AU)"


# ── Fetch functions ───────────────────────────────────────────────
def fetch_asteroids(days_ahead=7):
    """
    Fetch near-Earth asteroids for next N days.
    Max 7 days per request.
    """
    days_ahead = min(days_ahead, 7)
    now        = datetime.now(timezone.utc)
    start_date = now.strftime("%Y-%m-%d")
    end_date   = (now + timedelta(
        days=days_ahead)).strftime("%Y-%m-%d")

    url    = f"{BASE_URL}/feed"
    params = {
        "start_date": start_date,
        "end_date":   end_date,
        "api_key":    NASA_API_KEY
    }

    try:
        print(f"  Fetching asteroids "
              f"{start_date} → {end_date}...")
        response = requests.get(
            url, params=params, timeout=15)
        response.raise_for_status()
        data      = response.json()
        asteroids = []

        for date_str, neos in data.get(
            "near_earth_objects", {}
        ).items():
            for neo in neos:
                asteroid = parse_asteroid(neo, date_str)
                if asteroid:
                    asteroids.append(asteroid)

        asteroids.sort(
            key=lambda x: x["miss_distance_km"])
        print(f"  Found {len(asteroids)} asteroids")
        return asteroids

    except Exception as e:
        print(f"  [ERROR] NASA API: {e}")
    print(f"  Returning {len(asteroids)} asteroids to caller")
    return asteroids
    return []


def fetch_asteroids_range(days_ahead=30):
    """
    Fetch asteroids for more than 7 days
    by making multiple requests.
    """
    all_asteroids = []
    start         = datetime.now(timezone.utc)
    chunk_size    = 7
    chunks        = math.ceil(days_ahead / chunk_size)

    print(f"  Fetching {days_ahead} days "
          f"in {chunks} requests...")

    for i in range(chunks):
        chunk_start = start + timedelta(
            days=i * chunk_size)
        chunk_end   = min(
            chunk_start + timedelta(days=chunk_size),
            start + timedelta(days=days_ahead)
        )

        start_str = chunk_start.strftime("%Y-%m-%d")
        end_str   = chunk_end.strftime("%Y-%m-%d")

        url    = f"{BASE_URL}/feed"
        params = {
            "start_date": start_str,
            "end_date":   end_str,
            "api_key":    NASA_API_KEY
        }

        try:
            response = requests.get(
                url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            for date_str, neos in data.get(
                "near_earth_objects", {}
            ).items():
                for neo in neos:
                    asteroid = parse_asteroid(
                        neo, date_str)
                    if asteroid:
                        all_asteroids.append(asteroid)

            print(f"  Chunk {i+1}/{chunks} "
                  f"({start_str} → {end_str}) ✅")

        except Exception as e:
            print(f"  Chunk {i+1}/{chunks} failed: {e}")
            continue

    # Remove duplicates by ID
    seen   = set()
    unique = []
    for a in all_asteroids:
        if a["id"] not in seen:
            seen.add(a["id"])
            unique.append(a)

    unique.sort(key=lambda x: (
        x["approach_date"],
        x["miss_distance_km"]
    ))

    print(f"  Total unique asteroids: {len(unique)}")
    return unique


def get_asteroid_stats(asteroids):
    """Get summary statistics."""
    if not asteroids:
        return {}

    lunar      = 384400
    hazardous  = [a for a in asteroids if a["hazardous"]]
    within_1ld = [a for a in asteroids
                  if a["miss_distance_km"] < lunar]
    within_5ld = [a for a in asteroids
                  if a["miss_distance_km"] < lunar * 5]
    closest    = min(asteroids,
                     key=lambda x: x["miss_distance_km"])
    fastest    = max(asteroids,
                     key=lambda x: x["velocity_km_s"])
    largest    = max(asteroids,
                     key=lambda x: x["diameter_km"])

    return {
        "total":           len(asteroids),
        "hazardous":       len(hazardous),
        "within_1ld":      len(within_1ld),
        "within_5ld":      len(within_5ld),
        "closest":         closest,
        "fastest":         fastest,
        "largest":         largest,
        "avg_distance_ld": round(
            sum(a["miss_distance_km"]
                for a in asteroids) /
            len(asteroids) / lunar, 1),
    }


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n  Asteroid Tracker")
    print(f"  API Key: "
          f"{'Custom' if NASA_API_KEY != 'DEMO_KEY' else 'DEMO_KEY'}\n")

    asteroids = fetch_asteroids(days_ahead=7)

    if not asteroids:
        print("  No data returned\n")
    else:
        stats = get_asteroid_stats(asteroids)
        print(f"\n  Total:     {stats['total']}")
        print(f"  Hazardous: {stats['hazardous']}")
        print(f"  Closest:   "
              f"{stats['closest']['name']} — "
              f"{format_distance(stats['closest']['miss_distance_km'])}")
        print(f"  Fastest:   "
              f"{stats['fastest']['name']} — "
              f"{stats['fastest']['velocity_km_s']} km/s")
        print(f"  Largest:   "
              f"{stats['largest']['name']} — "
              f"{stats['largest']['diameter_m']}m\n")

        print(f"  {'Name':<35} {'Distance':<20} "
              f"{'Size':>8}m  {'Hazardous'}")
        print("  " + "─" * 75)
        for a in asteroids[:10]:
            haz = "⚠️ YES" if a["hazardous"] else "No"
            print(
                f"  {a['name']:<35} "
                f"{format_distance(a['miss_distance_km']):<20} "
                f"{a['diameter_m']:>8}   {haz}"
            )
        print()