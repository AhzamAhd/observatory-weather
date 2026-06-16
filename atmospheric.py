import math

# Wavelength seeing is referenced to (V band, 500 nm).
_SEEING_WAVELENGTH_M = 500e-9


def turbulence_integral(wind_speed_ms, humidity_pct, altitude_m):
    """
    Estimate the integrated refractive-index structure constant
    ∫ Cn²(h) dh  (units m^(1/3)) for a site.

    Uses a Hufnagel–Valley-style decomposition into a high-altitude
    (free-atmosphere) term driven by upper-level wind and a
    boundary-layer/surface term driven by ground wind and humidity.
    The site's own elevation removes the part of the atmospheric
    column that lies below it, so high sites integrate less
    turbulence.

    Calibrated so that a high, dry, calm site (~4200 m, ~3 m/s,
    ~20% RH) yields r0 ≈ 15–20 cm (seeing ≈ 0.6–0.8″) and a low,
    windy, humid site yields seeing ≈ 2–3″.
    """
    if wind_speed_ms is None:
        wind_speed_ms = 5.0
    if humidity_pct is None:
        humidity_pct = 50.0
    if altitude_m is None:
        altitude_m = 0.0

    # Free-atmosphere (high-altitude) floor — the irreducible
    # turbulence above any site, driven by upper-level wind. ~1e-13
    # m^(1/3) corresponds to the best ground-layer-free seeing.
    v_wind = 5.0 + wind_speed_ms
    high = 1.2e-13 * (v_wind / 12.0) ** 2

    # Boundary-layer / surface term. Ground turbulence dominates
    # real seeing; grows with wind shear and humidity (moist,
    # unstable surface layer), and is suppressed at high, thin sites
    # which sit above much of the surface layer.
    surface_strength = 9.0e-13
    wind_term   = 1.0 + (wind_speed_ms / 8.0) ** 2
    humid_term  = 1.0 + max(0.0, humidity_pct - 40.0) / 60.0
    column_term = math.exp(-altitude_m / 2500.0)
    surface = surface_strength * wind_term * humid_term * column_term

    cn2_integral = high + surface
    return max(1e-14, cn2_integral)


def fried_parameter(cn2_integral, wavelength_m=_SEEING_WAVELENGTH_M,
                    airmass=1.0):
    """
    Fried parameter r0 (metres) from the turbulence integral:

        r0 = (0.423 * k² * X * ∫Cn² dh) ^ (-3/5)

    where k = 2π/λ is the wavenumber and X the airmass (sec ζ).
    Larger r0 = better seeing.
    """
    k = 2.0 * math.pi / wavelength_m
    r0 = (0.423 * k ** 2 * airmass * cn2_integral) ** (-3.0 / 5.0)
    return r0


def calculate_seeing(temperature_c, wind_speed_ms,
                     humidity_pct, altitude_m=0,
                     airmass=1.0,
                     wavelength_nm=500.0):
    """
    Estimate atmospheric seeing (FWHM, arcsec) from the Fried
    parameter:

        θ = 0.98 * λ / r0      (radians)  →  × 206265 → arcsec

    r0 is derived from a Hufnagel–Valley-style Cn² integral
    (see turbulence_integral / fried_parameter). Lower θ = better.
    Exceptional < 0.5, Excellent < 1.0, Good 1.0–1.5,
    Average 1.5–2.5, Poor > 2.5 arcsec.

    temperature_c is retained for signature compatibility and a
    small cold-air stability bonus.
    """
    if any(v is None for v in [
        temperature_c, wind_speed_ms, humidity_pct
    ]):
        return None

    wavelength_m = wavelength_nm * 1e-9
    cn2 = turbulence_integral(wind_speed_ms, humidity_pct, altitude_m)
    r0  = fried_parameter(cn2, wavelength_m, max(1.0, airmass))

    # Seeing FWHM in arcseconds.
    theta_rad    = 0.98 * wavelength_m / r0
    seeing_arcsec = theta_rad * 206265.0

    # Small stability bonus: very cold, stable air tends to give
    # marginally tighter seeing (well-documented at polar/high sites).
    if temperature_c < -5:
        seeing_arcsec *= 0.95
    elif temperature_c < 5:
        seeing_arcsec *= 0.98

    return round(max(0.3, min(5.0, seeing_arcsec)), 2)

def seeing_quality(seeing_arcsec):
    if seeing_arcsec is None:
        return "Unknown"
    if seeing_arcsec < 0.5:   return "Exceptional"
    elif seeing_arcsec < 1.0: return "Excellent"
    elif seeing_arcsec < 1.5: return "Good"
    elif seeing_arcsec < 2.5: return "Average"
    elif seeing_arcsec < 3.5: return "Poor"
    else:                      return "Very Poor"

def seeing_color(seeing_arcsec):
    if seeing_arcsec is None: return "#888780"
    if seeing_arcsec < 0.5:   return "#1D9E75"
    elif seeing_arcsec < 1.0: return "#5DCAA5"
    elif seeing_arcsec < 1.5: return "#378ADD"
    elif seeing_arcsec < 2.5: return "#EF9F27"
    elif seeing_arcsec < 3.5: return "#E24B4A"
    else:                      return "#993C1D"

def calculate_pwv(surface_pressure, humidity_pct,
                  temperature_c, altitude_m=0):
    """
    Estimate Precipitable Water Vapor in millimetres.
    Critical for infrared and radio astronomy.
    Lower PWV = better for IR/radio work.
    Excellent < 2mm, Good 2-5mm, Poor > 10mm.
    """
    if any(v is None for v in [
        surface_pressure, humidity_pct, temperature_c
    ]):
        return None

    # Saturation vapour pressure using Magnus formula
    a, b = 17.625, 243.04
    svp  = 6.112 * math.exp(
        (a * temperature_c) / (b + temperature_c)
    )

    # Actual vapour pressure
    avp  = (humidity_pct / 100) * svp

    # Scale height approximation (km)
    scale_height = 2.0 * math.exp(-altitude_m / 8000)

    # PWV in mm
    pwv = 0.1 * avp * scale_height
    return round(max(0.1, pwv), 2)

def pwv_quality(pwv_mm):
    if pwv_mm is None:
        return "Unknown"
    if pwv_mm < 1.0:    return "Exceptional"
    elif pwv_mm < 2.0:  return "Excellent"
    elif pwv_mm < 5.0:  return "Good"
    elif pwv_mm < 10.0: return "Average"
    elif pwv_mm < 20.0: return "Poor"
    else:               return "Very Poor"

def pwv_color(pwv_mm):
    if pwv_mm is None:  return "#888780"
    if pwv_mm < 1.0:    return "#1D9E75"
    elif pwv_mm < 2.0:  return "#5DCAA5"
    elif pwv_mm < 5.0:  return "#378ADD"
    elif pwv_mm < 10.0: return "#EF9F27"
    elif pwv_mm < 20.0: return "#E24B4A"
    else:               return "#993C1D"

def calculate_jet_stream_impact(jet_stream_ms, latitude):
    """
    Assess jet stream impact on seeing.
    Jet stream at 250hPa (~10km altitude).
    Strong jet stream directly overhead = bad seeing.
    """
    if jet_stream_ms is None:
        return None, "Unknown"

    # Jet stream is strongest at 30-60 degrees latitude
    lat_factor = abs(math.sin(math.radians(abs(latitude) - 45)))
    impact_ms  = jet_stream_ms * (1 - lat_factor * 0.3)

    if impact_ms < 20:   impact = "Negligible"
    elif impact_ms < 40: impact = "Low"
    elif impact_ms < 60: impact = "Moderate"
    elif impact_ms < 80: impact = "High"
    else:                impact = "Severe"

    return round(impact_ms, 1), impact

def jet_stream_color(impact):
    return {
        "Negligible": "#1D9E75",
        "Low":        "#5DCAA5",
        "Moderate":   "#EF9F27",
        "High":       "#E24B4A",
        "Severe":     "#993C1D",
        "Unknown":    "#888780"
    }.get(impact, "#888780")

def get_full_atmospheric_analysis(record):
    """
    Run all three calculations for one observatory record.
    """
    seeing     = calculate_seeing(
        record.get("temperature_c"),
        record.get("wind_speed_ms"),
        record.get("humidity_pct"),
        record.get("altitude_m", 0)
    )
    pwv        = calculate_pwv(
        record.get("surface_pressure"),
        record.get("humidity_pct"),
        record.get("temperature_c"),
        record.get("altitude_m", 0)
    )
    jet_ms, jet_impact = calculate_jet_stream_impact(
        record.get("jet_stream_ms"),
        record.get("latitude", 0)
    )

    return {
        "seeing_arcsec":    seeing,
        "seeing_quality":   seeing_quality(seeing),
        "seeing_color":     seeing_color(seeing),
        "pwv_mm":           pwv,
        "pwv_quality":      pwv_quality(pwv),
        "pwv_color":        pwv_color(pwv),
        "jet_stream_ms":    jet_ms,
        "jet_impact":       jet_impact,
        "jet_color":        jet_stream_color(jet_impact),
    }


if __name__ == "__main__":
    test = {
        "temperature_c":    7.2,
        "wind_speed_ms":    2.11,
        "humidity_pct":     74.0,
        "altitude_m":       4205,
        "surface_pressure": 620.0,
        "jet_stream_ms":    35.0,
        "latitude":         19.82
    }
    result = get_full_atmospheric_analysis(test)
    print("\n Atmospheric Analysis — Mauna Kea\n")
    print(f"  Seeing    : {result['seeing_arcsec']}\" "
          f"[{result['seeing_quality']}]")
    print(f"  PWV       : {result['pwv_mm']} mm "
          f"[{result['pwv_quality']}]")
    print(f"  Jet stream: {result['jet_stream_ms']} m/s "
          f"[{result['jet_impact']}]\n")