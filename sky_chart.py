import ephem
import math
from datetime import datetime

# ── Bright stars catalogue ────────────────────────────────────────
BRIGHT_STARS = [
    ("Sirius",      "CMa", -1.46, ephem.star("Sirius")),
    ("Canopus",     "Car", -0.72, ephem.star("Canopus")),
    ("Arcturus",    "Boo", -0.05, ephem.star("Arcturus")),
    ("Vega",        "Lyr",  0.03, ephem.star("Vega")),
    ("Capella",     "Aur",  0.08, ephem.star("Capella")),
    ("Rigel",       "Ori",  0.13, ephem.star("Rigel")),
    ("Procyon",     "CMi",  0.34, ephem.star("Procyon")),
    ("Betelgeuse",  "Ori",  0.50, ephem.star("Betelgeuse")),
    ("Achernar",    "Eri",  0.46, ephem.star("Achernar")),
    ("Altair",      "Aql",  0.77, ephem.star("Altair")),
    ("Acrux",       "Cru",  0.87, ephem.star("Acrux")),
    ("Aldebaran",   "Tau",  0.87, ephem.star("Aldebaran")),
    ("Antares",     "Sco",  1.09, ephem.star("Antares")),
    ("Spica",       "Vir",  0.98, ephem.star("Spica")),
    ("Pollux",      "Gem",  1.16, ephem.star("Pollux")),
    ("Fomalhaut",   "PsA",  1.16, ephem.star("Fomalhaut")),
    ("Deneb",       "Cyg",  1.25, ephem.star("Deneb")),
    ("Mimosa",      "Cru",  1.25, ephem.star("Mimosa")),
    ("Regulus",     "Leo",  1.36, ephem.star("Regulus")),
    ("Castor",      "Gem",  1.58, ephem.star("Castor")),
    ("Bellatrix",   "Ori",  1.64, ephem.star("Bellatrix")),
    ("Alnilam",     "Ori",  1.70, ephem.star("Alnilam")),
    ("Alnitak",     "Ori",  1.74, ephem.star("Alnitak")),
    ("Alioth",      "UMa",  1.77, ephem.star("Alioth")),
    ("Dubhe",       "UMa",  1.79, ephem.star("Dubhe")),
    ("Alphard",     "Hya",  1.99, ephem.star("Alphard")),
    ("Hamal",       "Ari",  2.01, ephem.star("Hamal")),
    ("Diphda",      "Cet",  2.04, ephem.star("Diphda")),
    ("Polaris",     "UMi",  1.98, ephem.star("Polaris")),
]

# ── Live camera feeds ─────────────────────────────────────────────
LIVE_CAMERA_IMAGES = {
    "5  Maunakea": {
        "name":        "Maunakea — NOAA All-sky Camera",
        "image_url":   "https://gml.noaa.gov/obop/mlo/livecam/north.jpg",
        "page_url":    "https://gml.noaa.gov/obop/mlo/livecam/livecam.html",
        "description": "Updates every 15 minutes",
        "credit":      "NOAA Global Monitoring Laboratory"
    },
}

OBSERVATORY_WEBSITES = {
    "5  Maunakea":
        "https://www.ifa.hawaii.edu/mko/",
    "7  La Palma":
        "https://www.ing.iac.es",
    "0  Cerro Tololo Observatory, La Serena":
        "https://www.ctio.noirlab.edu",
    "2  Micro Palomar, Reilhanette":
        "https://www.palomar.caltech.edu",
    "8  Pacific Lutheran University Keck Observatory":
        "https://www.keckobservatory.org",
    "4  Alma-Ata":
        "https://fai.kz",
    "5  Santiago-Cerro El Roble":
        "https://www.das.uchile.cl",
    "8  Santiago-Cerro Calán":
        "https://www.das.uchile.cl",
    "0  Cerro del Viento, Badajoz":
        "https://www.astrofoto.es",
}

def get_observatory_url(observatory_name):
    """
    Get website URL for an observatory.
    Returns known URL or generates a Google search link.
    """
    if observatory_name in OBSERVATORY_WEBSITES:
        return OBSERVATORY_WEBSITES[observatory_name]

    # Generate Google search for unknown observatories
    import urllib.parse
    query = urllib.parse.quote(
        f"{observatory_name} observatory official website")
    return f"https://www.google.com/search?q={query}"

def get_live_camera(observatory_name):
    """
    Get live camera data for an observatory if available.
    Returns None if no camera feed exists.
    """
    return LIVE_CAMERA_IMAGES.get(observatory_name)


# ── Planets ───────────────────────────────────────────────────────
PLANETS = [
    ("Mercury", ephem.Mercury(), "#B5B5B5", 6),
    ("Venus",   ephem.Venus(),   "#FFE4B5", 8),
    ("Mars",    ephem.Mars(),    "#FF6347", 7),
    ("Jupiter", ephem.Jupiter(), "#FAD5A5", 9),
    ("Saturn",  ephem.Saturn(),  "#F4C542", 7),
    ("Uranus",  ephem.Uranus(),  "#7FDBFF", 5),
    ("Neptune", ephem.Neptune(), "#4169E1", 4),
]

# ── Constellation lines ───────────────────────────────────────────
# Each tuple is (star1_name, star2_name)
CONSTELLATION_LINES = [
    # Orion
    ("Betelgeuse", "Alnilam"),
    ("Rigel",      "Alnilam"),
    ("Alnilam",    "Alnitak"),
    ("Bellatrix",  "Betelgeuse"),
    # Ursa Major
    ("Dubhe",  "Alioth"),
    # Southern Cross
    ("Acrux",  "Mimosa"),
]

def get_observer(lat, lon):
    obs          = ephem.Observer()
    obs.lat      = str(lat)
    obs.long     = str(lon)
    obs.date     = datetime.utcnow().strftime(
        "%Y/%m/%d %H:%M:%S")
    obs.pressure = 0
    return obs

def alt_az_to_polar(alt_deg, az_deg):
    """
    Convert altitude/azimuth to polar chart coordinates.
    r=0 at zenith, r=1 at horizon.
    theta=0 at North, increases clockwise.
    """
    r     = 1.0 - (alt_deg / 90.0)
    theta = math.radians(az_deg)
    return theta, r

def compute_sky(lat, lon, object_name=None):
    """
    Compute positions of all objects for the sky chart.
    Returns dicts of stars, planets, moon, sun positions.
    """
    obs = get_observer(lat, lon)

    # ── Stars ─────────────────────────────────────────────
    star_data = []
    star_positions = {}  # for constellation lines

    for name, constellation, mag, star in BRIGHT_STARS:
        try:
            star.compute(obs)
            alt = math.degrees(float(star.alt))
            az  = math.degrees(float(star.az))

            if alt < -5:
                continue

            theta, r = alt_az_to_polar(alt, az)

            # Size based on magnitude
            size = max(2, int(8 - mag * 1.5))

            # Dimming near horizon
            opacity = min(1.0, (alt + 5) / 20)

            star_data.append({
                "name":         name,
                "constellation": constellation,
                "magnitude":    mag,
                "altitude":     round(alt, 1),
                "azimuth":      round(az, 1),
                "theta":        theta,
                "r":            r,
                "size":         size,
                "opacity":      round(opacity, 2),
                "visible":      alt >= 0
            })
            star_positions[name] = (theta, r, alt >= 0)

        except Exception:
            continue

    # ── Planets ───────────────────────────────────────────
    planet_data = []
    for name, planet, color, base_size in PLANETS:
        try:
            planet.compute(obs)
            alt = math.degrees(float(planet.alt))
            az  = math.degrees(float(planet.az))

            theta, r = alt_az_to_polar(alt, az)

            planet_data.append({
                "name":      name,
                "altitude":  round(alt, 1),
                "azimuth":   round(az, 1),
                "theta":     theta,
                "r":         r,
                "color":     color,
                "size":      base_size,
                "visible":   alt >= 0,
                "magnitude": round(planet.mag, 1)
            })
        except Exception:
            continue

    # ── Moon ──────────────────────────────────────────────
    moon = ephem.Moon()
    moon.compute(obs)
    moon_alt = math.degrees(float(moon.alt))
    moon_az  = math.degrees(float(moon.az))
    moon_theta, moon_r = alt_az_to_polar(moon_alt, moon_az)

    moon_data = {
        "altitude":  round(moon_alt, 1),
        "azimuth":   round(moon_az, 1),
        "theta":     moon_theta,
        "r":         moon_r,
        "phase":     round(moon.phase, 1),
        "visible":   moon_alt >= 0
    }

    # ── Sun ───────────────────────────────────────────────
    sun = ephem.Sun()
    sun.compute(obs)
    sun_alt = math.degrees(float(sun.alt))
    sun_az  = math.degrees(float(sun.az))
    sun_theta, sun_r = alt_az_to_polar(sun_alt, sun_az)

    sun_data = {
        "altitude": round(sun_alt, 1),
        "azimuth":  round(sun_az, 1),
        "theta":    sun_theta,
        "r":        sun_r,
        "visible":  sun_alt >= 0
    }

    # ── Target object ─────────────────────────────────────
    target_data = None
    if object_name:
        from object_visibility import (
            calculate_visibility, OBJECTS)
        obj_info = OBJECTS.get(object_name)
        if obj_info:
            vis = calculate_visibility(lat, lon, object_name)
            if vis and vis.get("altitude_deg", -90) > -10:
                alt = vis["altitude_deg"]
                az  = vis["azimuth_deg"]
                theta, r = alt_az_to_polar(alt, az)
                target_data = {
                    "name":     object_name,
                    "altitude": alt,
                    "azimuth":  az,
                    "theta":    theta,
                    "r":        r,
                    "visible":  alt >= 0
                }

    # ── Constellation lines ───────────────────────────────
    line_data = []
    for star1, star2 in CONSTELLATION_LINES:
        if star1 in star_positions and star2 in star_positions:
            t1, r1, vis1 = star_positions[star1]
            t2, r2, vis2 = star_positions[star2]
            if vis1 and vis2:
                line_data.append({
                    "star1": star1,
                    "star2": star2,
                    "t1": t1, "r1": r1,
                    "t2": t2, "r2": r2
                })

    # ── Sky state ─────────────────────────────────────────
    if sun_alt > 0:
        sky_state  = "day"
        sky_color  = "#1a3a5c"
    elif sun_alt > -6:
        sky_state  = "civil"
        sky_color  = "#0d1b2a"
    elif sun_alt > -18:
        sky_state  = "twilight"
        sky_color  = "#050d1a"
    else:
        sky_state  = "night"
        sky_color  = "#010408"

    return {
        "stars":           star_data,
        "planets":         planet_data,
        "moon":            moon_data,
        "sun":             sun_data,
        "target":          target_data,
        "constellation_lines": line_data,
        "sky_state":       sky_state,
        "sky_color":       sky_color,
        "computed_at":     datetime.utcnow().strftime(
            "%Y-%m-%d %H:%M UTC"),
        "lat":             lat,
        "lon":             lon
    }