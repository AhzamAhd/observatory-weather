import ephem
import math
from datetime import datetime

# ── Major astronomical objects with their coordinates ─────────────
OBJECTS = {
    # Planets
    "Mercury":          {"type": "planet", "obj": ephem.Mercury},
    "Venus":            {"type": "planet", "obj": ephem.Venus},
    "Mars":             {"type": "planet", "obj": ephem.Mars},
    "Jupiter":          {"type": "planet", "obj": ephem.Jupiter},
    "Saturn":           {"type": "planet", "obj": ephem.Saturn},
    "Uranus":           {"type": "planet", "obj": ephem.Uranus},
    "Neptune":          {"type": "planet", "obj": ephem.Neptune},

    # Messier deep sky objects
    "Andromeda Galaxy (M31)":     {"type": "deep_sky", "ra": "0:42:44",  "dec": "41:16:09"},
    "Orion Nebula (M42)":         {"type": "deep_sky", "ra": "5:35:17",  "dec": "-5:23:28"},
    "Pleiades (M45)":             {"type": "deep_sky", "ra": "3:47:24",  "dec": "24:07:00"},
    "Whirlpool Galaxy (M51)":     {"type": "deep_sky", "ra": "13:29:53", "dec": "47:11:43"},
    "Ring Nebula (M57)":          {"type": "deep_sky", "ra": "18:53:35", "dec": "33:01:45"},
    "Crab Nebula (M1)":           {"type": "deep_sky", "ra": "5:34:32",  "dec": "22:00:52"},
    "Globular Cluster (M13)":     {"type": "deep_sky", "ra": "16:41:41", "dec": "36:27:37"},
    "Sombrero Galaxy (M104)":     {"type": "deep_sky", "ra": "12:39:59", "dec": "-11:37:23"},
    "Triangulum Galaxy (M33)":    {"type": "deep_sky", "ra": "1:33:51",  "dec": "30:39:37"},
    "Lagoon Nebula (M8)":         {"type": "deep_sky", "ra": "18:03:37", "dec": "-24:23:12"},
    "Eagle Nebula (M16)":         {"type": "deep_sky", "ra": "18:18:48", "dec": "-13:47:00"},
    "Dumbbell Nebula (M27)":      {"type": "deep_sky", "ra": "19:59:36", "dec": "22:43:16"},
    "Pinwheel Galaxy (M101)":     {"type": "deep_sky", "ra": "14:03:13", "dec": "54:20:56"},
    "Beehive Cluster (M44)":      {"type": "deep_sky", "ra": "8:40:24",  "dec": "19:40:00"},
    "Omega Nebula (M17)":         {"type": "deep_sky", "ra": "18:20:26", "dec": "-16:10:36"},

    # Famous stars
    "Sirius":           {"type": "star", "ra": "6:45:09",  "dec": "-16:42:58"},
    "Betelgeuse":       {"type": "star", "ra": "5:55:10",  "dec": "7:24:25"},
    "Rigel":            {"type": "star", "ra": "5:14:32",  "dec": "-8:12:06"},
    "Vega":             {"type": "star", "ra": "18:36:56", "dec": "38:47:01"},
    "Arcturus":         {"type": "star", "ra": "14:15:40", "dec": "19:10:57"},
    "Polaris":          {"type": "star", "ra": "2:31:49",  "dec": "89:15:51"},
    "Antares":          {"type": "star", "ra": "16:29:24", "dec": "-26:25:55"},
    "Aldebaran":        {"type": "star", "ra": "4:35:55",  "dec": "16:30:33"},

    # Other
    "Galactic Centre":  {"type": "deep_sky", "ra": "17:45:40", "dec": "-29:00:28"},
    "Large Magellanic Cloud": {"type": "deep_sky", "ra": "5:23:34", "dec": "-69:45:22"},
    "Small Magellanic Cloud": {"type": "deep_sky", "ra": "0:52:45", "dec": "-72:49:43"},
}

# ── Minimum altitude requirements by object type ──────────────────
MIN_ALTITUDE = {
    "planet":   15,   # planets need at least 15° above horizon
    "deep_sky": 20,   # deep sky needs at least 20° to avoid atmosphere
    "star":     10,   # stars can be observed lower
}

def get_ephem_object(name, obj_info):
    if obj_info["type"] == "planet":
        return obj_info["obj"]()
    else:
        fixed = ephem.FixedBody()
        fixed.name  = name
        fixed._ra   = obj_info["ra"]
        fixed._dec  = obj_info["dec"]
        fixed._epoch = ephem.J2000
        return fixed

def calculate_visibility(lat, lon, object_name, date=None):
    if date is None:
        date = datetime.utcnow()

    obj_info = OBJECTS.get(object_name)
    if not obj_info:
        return None

    obs = ephem.Observer()
    obs.lat   = str(lat)
    obs.long  = str(lon)
    obs.date  = date.strftime("%Y/%m/%d %H:%M:%S")
    obs.pressure = 0  # ignore atmospheric refraction for simplicity

    target     = get_ephem_object(object_name, obj_info)
    target.compute(obs)

    altitude_deg = math.degrees(float(target.alt))
    azimuth_deg  = math.degrees(float(target.az))
    min_alt      = MIN_ALTITUDE.get(obj_info["type"], 15)
    is_visible   = altitude_deg >= min_alt

    # Find rise and set times
    try:
        obs.horizon = str(min_alt)
        rise_time   = obs.next_rising(target).datetime()
        set_time    = obs.next_setting(target).datetime()
        hours_up    = (set_time - rise_time).total_seconds() / 3600
        if hours_up < 0:
            hours_up += 24
    except Exception:
        rise_time = None
        set_time  = None
        hours_up  = 0

    # Cardinal direction
    if 315 <= azimuth_deg or azimuth_deg < 45:   direction = "N"
    elif 45 <= azimuth_deg < 135:                 direction = "E"
    elif 135 <= azimuth_deg < 225:                direction = "S"
    else:                                          direction = "W"

    # Visibility quality
    if altitude_deg >= 60:    visibility_quality = "Excellent"
    elif altitude_deg >= 40:  visibility_quality = "Good"
    elif altitude_deg >= min_alt: visibility_quality = "Marginal"
    else:                     visibility_quality = "Below horizon"

    return {
        "object":             object_name,
        "type":               obj_info["type"],
        "altitude_deg":       round(altitude_deg, 1),
        "azimuth_deg":        round(azimuth_deg, 1),
        "direction":          direction,
        "is_visible":         is_visible,
        "visibility_quality": visibility_quality,
        "rise_time":          rise_time.strftime("%H:%M UTC") if rise_time else "N/A",
        "set_time":           set_time.strftime("%H:%M UTC")  if set_time  else "N/A",
        "hours_visible":      round(max(0, hours_up), 1),
        "min_altitude":       min_alt
    }

def get_best_observatories_for_object(object_name, observatories_df):
    results = []
    for _, row in observatories_df.iterrows():
        try:
            vis = calculate_visibility(
                row["latitude"],
                row["longitude"],
                object_name
            )
            if vis:
                results.append({
                    "observatory":        row["observatory"],
                    "country":            row["country"],
                    "weather_score":      row["observation_score"],
                    "altitude_deg":       vis["altitude_deg"],
                    "direction":          vis["direction"],
                    "is_visible":         vis["is_visible"],
                    "visibility_quality": vis["visibility_quality"],
                    "rise_time":          vis["rise_time"],
                    "set_time":           vis["set_time"],
                    "hours_visible":      vis["hours_visible"],
                })
        except Exception:
            continue

    import pandas as pd
    df = pd.DataFrame(results)
    if df.empty:
        return df

    # Combined score — weather + visibility altitude
    df["combined_score"] = (
        df["weather_score"] * 0.6 +
        df["altitude_deg"].clip(0, 90) / 90 * 100 * 0.4
    ).round(1)

    return df[df["is_visible"]].sort_values(
        "combined_score", ascending=False
    )

if __name__ == "__main__":
    print("\n Testing object visibility calculator...\n")
    result = calculate_visibility(19.8207, -155.4681, "Orion Nebula (M42)")
    if result:
        print(f"  Object   : {result['object']}")
        print(f"  Altitude : {result['altitude_deg']}°")
        print(f"  Direction: {result['direction']}")
        print(f"  Visible  : {result['is_visible']}")
        print(f"  Quality  : {result['visibility_quality']}")
        print(f"  Rises at : {result['rise_time']}")
        print(f"  Sets at  : {result['set_time']}")
        print(f"  Hours up : {result['hours_visible']}h\n")