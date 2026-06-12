import math
import ephem
import numpy as np
from datetime import datetime, timezone, timedelta
from object_visibility import OBJECTS

def altitude_to_airmass(altitude_deg):
    """
    Convert altitude above horizon to airmass.
    Uses Pickering (2002) formula — more accurate
    than simple 1/sin(alt) near horizon.
    """
    if altitude_deg <= 0:
        return None

    # Pickering formula
    alt_rad = math.radians(altitude_deg)
    airmass = 1.0 / (
        math.sin(math.radians(
            altitude_deg +
            244.0 / (165.0 + 47.0 * altitude_deg**1.1)
        ))
    )
    return round(airmass, 3)

def airmass_to_altitude(airmass):
    """Convert airmass back to approximate altitude."""
    if airmass <= 1.0:
        return 90.0
    # Approximate inverse
    alt = math.degrees(math.asin(1.0 / airmass))
    return round(alt, 1)

def airmass_quality(airmass):
    """Rate the airmass value."""
    if airmass is None:   return "Below horizon"
    elif airmass <= 1.1:  return "Excellent"
    elif airmass <= 1.5:  return "Good"
    elif airmass <= 2.0:  return "Acceptable"
    elif airmass <= 3.0:  return "Poor"
    else:                 return "Very Poor"

def airmass_color(airmass):
    """Color for airmass value."""
    if airmass is None:   return "#888888"
    elif airmass <= 1.1:  return "#1D9E75"
    elif airmass <= 1.5:  return "#378ADD"
    elif airmass <= 2.0:  return "#EF9F27"
    elif airmass <= 3.0:  return "#E24B4A"
    else:                 return "#880000"

# Reference extinction coefficients (mag/airmass) at the
# 2000 m reference altitude, per filter band. Calibrated so
# that the altitude scaling reproduces published mean
# extinction at ORM La Palma (2326 m): U~0.46, B~0.22,
# V~0.12, R~0.09, I~0.05 (King 1985; ORM site monitoring),
# consistent with ESO Paranal (V~0.11) once scaled.
EXTINCTION_REFERENCE = {
    "U": 0.479,  # UV
    "B": 0.229,  # Blue
    "V": 0.125,  # Visual (green)
    "R": 0.094,  # Red
    "I": 0.052,  # Near-IR
    "J": 0.031,  # IR
    "H": 0.021,  # IR
    "K": 0.015,  # IR
}

# Altitude (m) the reference coefficients above are tied to.
_REFERENCE_ALTITUDE_M = 2000.0


def site_extinction_scale(altitude_m):
    """
    Scale factor for atmospheric extinction based on site
    altitude. Higher, drier sites sit above more of the
    atmosphere, so extinction drops with elevation.

    Returns a multiplier applied to the reference (2000 m)
    extinction coefficients. The atmospheric column scales
    roughly as exp(-h / H) with scale height H ≈ 8000 m, so
    we anchor that ratio to the 2000 m reference and clamp to
    a sensible range.
    """
    if altitude_m is None or altitude_m <= 0:
        # Sea-level / unknown — most extinction.
        altitude_m = 0.0

    H = 8000.0  # atmospheric scale height in metres
    scale = math.exp(-(altitude_m - _REFERENCE_ALTITUDE_M) / H)
    # Clamp: dry 4200 m peak ~0.78x, low coastal site ~1.65x
    return max(0.70, min(1.8, scale))


def extinction_coefficient(altitude_m=_REFERENCE_ALTITUDE_M,
                           filter_band="V"):
    """
    Site- and filter-specific extinction coefficient k
    (magnitudes per airmass).
    """
    base = EXTINCTION_REFERENCE.get(filter_band, 0.18)
    return round(base * site_extinction_scale(altitude_m), 4)


def extinction_magnitudes(airmass, filter_band="V",
                          altitude_m=_REFERENCE_ALTITUDE_M):
    """
    Calculate atmospheric extinction in magnitudes.
    How much dimmer an object appears due to atmosphere.
    Extinction now scales with site altitude.
    """
    if airmass is None:
        return None

    coeff = extinction_coefficient(altitude_m, filter_band)
    return round(coeff * airmass, 3)

def get_ephem_body(object_name, observer):
    """
    Get ephem body for any object type.
    Handles planets, deep sky objects and exoplanets.
    """
    obj_info = OBJECTS.get(object_name)
    if not obj_info:
        return None

    try:
        # Planet — has ephem class directly
        if "obj" in obj_info:
            body = obj_info["obj"]()
            body.compute(observer)
            return body

        # Deep sky — has RA/Dec strings
        elif "ra" in obj_info and "dec" in obj_info:
            body      = ephem.FixedBody()
            body._ra  = ephem.hours(
                str(obj_info["ra"]))
            body._dec = ephem.degrees(
                str(obj_info["dec"]))
            body.compute(observer)
            return body

        # Exoplanet — has ra_deg/dec_deg floats
        elif "ra_deg" in obj_info:
            body      = ephem.FixedBody()
            body._ra  = ephem.degrees(
                str(obj_info["ra_deg"]))
            body._dec = ephem.degrees(
                str(obj_info["dec_deg"]))
            body.compute(observer)
            return body

    except Exception as e:
        return None

    return None


def get_object_airmass_curve(
    object_name, lat, lon, alt_m,
    date=None, hours=12
):
    """
    Calculate airmass curve for an object over time.
    Returns readings every 30 minutes for N hours.
    """
    observer           = ephem.Observer()
    observer.lat       = str(lat)
    observer.long      = str(lon)
    observer.elevation = float(alt_m)
    observer.pressure  = 0

    if date is None:
        now = datetime.now(timezone.utc).replace(
            tzinfo=None)
    else:
        now = date

    results = []
    for h in range(hours * 2):  # Every 30 minutes
        t = now + timedelta(minutes=h * 30)
        observer.date = t.strftime(
            "%Y/%m/%d %H:%M:%S")

        try:
            body = get_ephem_body(object_name, observer)
            if body is None:
                continue

            alt_deg = math.degrees(float(body.alt))
            az_deg  = math.degrees(float(body.az))
            airmass = altitude_to_airmass(alt_deg)

            sun = ephem.Sun()
            sun.compute(observer)
            sun_alt = math.degrees(float(sun.alt))

            results.append({
                "time":       t.strftime("%H:%M"),
                "time_dt":    t,
                "altitude":   round(alt_deg, 1),
                "azimuth":    round(az_deg, 1),
                "airmass":    airmass,
                "quality":    airmass_quality(airmass),
                "color":      airmass_color(airmass),
                "sun_alt":    round(sun_alt, 1),
                "is_dark":    sun_alt < -18,
                "is_night":   sun_alt < 0,
                "extinction": extinction_magnitudes(
                    airmass, altitude_m=alt_m),
            })
        except Exception:
            continue

    return results

def get_best_observation_window(airmass_curve):
    """
    Find the best window for observation
    based on airmass curve.
    """
    dark_points = [
        p for p in airmass_curve
        if p["is_dark"] and p["airmass"] is not None
    ]

    if not dark_points:
        return None

    best = min(dark_points, key=lambda x: x["airmass"])
    good = [p for p in dark_points if p["airmass"] <= 2.0]

    return {
        "best_time":    best["time"],
        "best_airmass": best["airmass"],
        "best_alt":     best["altitude"],
        "good_hours":   len(good) * 0.5,
        "window_start": good[0]["time"] if good else None,
        "window_end":   good[-1]["time"] if good else None,
    }

def compare_objects_airmass(
    object_names, lat, lon, alt_m
):
    """
    Compare airmass for multiple objects right now.
    """
    observer           = ephem.Observer()
    observer.lat       = str(lat)
    observer.long      = str(lon)
    observer.elevation = float(alt_m)
    observer.pressure  = 0
    observer.date      = datetime.now(
        timezone.utc).replace(tzinfo=None
        ).strftime("%Y/%m/%d %H:%M:%S")

    results = []
    for name in object_names:
        obj_info = OBJECTS.get(name)
        if not obj_info:
            continue

        try:
            body = get_ephem_body(name, observer)
            if body is None:
                continue

            alt_deg = math.degrees(float(body.alt))
            az_deg  = math.degrees(float(body.az))
            airmass = altitude_to_airmass(alt_deg)

            results.append({
                "object":     name,
                "type":       obj_info.get("type", ""),
                "altitude":   round(alt_deg, 1),
                "azimuth":    round(az_deg, 1),
                "airmass":    airmass,
                "quality":    airmass_quality(airmass),
                "color":      airmass_color(airmass),
                "extinction": extinction_magnitudes(
                    airmass, altitude_m=alt_m),
                "visible":    alt_deg > 10,
            })
        except Exception:
            continue

    return sorted(
        results,
        key=lambda x: x["airmass"] or 99
    )


if __name__ == "__main__":
    print("\n  Airmass Calculator Test")
    print("  Location: Mauna Kea, Hawaii\n")

    lat, lon, alt = 19.8207, -155.4681, 4205

    # Test single object curve
    print("  M42 (Orion Nebula) airmass curve:\n")
    curve = get_object_airmass_curve(
        "M42 — Orion Nebula",
        lat, lon, alt, hours=12
    )

    print(f"  {'Time':<8} {'Alt':<8} "
          f"{'Airmass':<10} {'Quality':<12} {'Dark?'}")
    print("  " + "─" * 50)
    for point in curve[::2]:  # Every hour
        dark = "🌑" if point["is_dark"] else "☀️"
        am   = (f"{point['airmass']:.2f}"
                if point["airmass"] else "—")
        print(
            f"  {point['time']:<8} "
            f"{point['altitude']:<8} "
            f"{am:<10} "
            f"{point['quality']:<12} "
            f"{dark}"
        )

    # Test multiple objects
    print("\n  Current airmass comparison:\n")
    objects = [
        "M42 — Orion Nebula",
        "M31 — Andromeda Galaxy",
        "Jupiter",
        "M45 — Pleiades"
    ]
    comparison = compare_objects_airmass(
        objects, lat, lon, alt)

    print(f"  {'Object':<25} {'Alt':<8} "
          f"{'Airmass':<10} {'Quality'}")
    print("  " + "─" * 55)
    for obj in comparison:
        am = (f"{obj['airmass']:.2f}"
              if obj["airmass"] else "Below horizon")
        print(
            f"  {obj['object']:<25} "
            f"{obj['altitude']:<8} "
            f"{am:<10} "
            f"{obj['quality']}"
        )
    print()