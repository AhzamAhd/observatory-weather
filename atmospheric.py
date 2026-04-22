import math

def calculate_seeing(temperature_c, wind_speed_ms,
                     humidity_pct, altitude_m=0):
    """
    Estimate atmospheric seeing in arcseconds.
    Based on simplified Fried parameter model.
    Lower = better. Excellent < 1.0, Good 1.0-2.0,
    Poor > 2.0 arcsec.
    """
    if any(v is None for v in [
        temperature_c, wind_speed_ms, humidity_pct
    ]):
        return None

    # Base seeing from wind (higher wind = worse seeing)
    wind_factor = 0.5 + (wind_speed_ms / 10) * 0.8

    # Humidity penalty (above 70% degrades seeing)
    if humidity_pct > 70:
        humidity_factor = 1 + (humidity_pct - 70) / 100
    else:
        humidity_factor = 1.0

    # Altitude bonus (higher sites have better seeing)
    altitude_factor = max(0.5, 1 - (altitude_m / 10000))

    # Temperature stability bonus
    # Very cold sites tend to have more stable air
    if temperature_c < -5:
        temp_factor = 0.85
    elif temperature_c < 5:
        temp_factor = 0.95
    else:
        temp_factor = 1.0

    seeing = (wind_factor * humidity_factor *
              altitude_factor * temp_factor)
    return round(max(0.3, min(5.0, seeing)), 2)

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