import math

# Wavelength seeing is referenced to (V band, 500 nm).
_SEEING_WAVELENGTH_M = 500e-9

# ── Physically-grounded seeing via the Tatarski Cn2 formulation ───────
# References:
#   Tatarski, V.I. (1971), "The Effects of the Turbulent Atmosphere on Wave
#     Propagation" — the C_T^2 = (c/Pr_t) L0^(4/3) Gamma^2 relation and the
#     optical conversion Cn^2 = (79e-6 P/T^2)^2 C_T^2.
#   Basu, S. & Holtslag, A.A.M. (2021), arXiv:2110.03439 — revisits/derives the
#     Tatarski C_T^2 formulation; notes it is valid for STABLY stratified
#     conditions (i.e. nighttime, when astronomers observe).
#   Fried, D.L. (1966), JOSA 56, 1372 — r0 = (0.423 k^2 X integral Cn^2 dh)^-3/5.
# This replaces the earlier hand-fitted Cn^2 heuristic with the published
# formalism, driven by REAL vertical gradients from Open-Meteo pressure levels
# (850/500 hPa). Where profile data is missing we fall back to the heuristic.
_G = 9.80665          # gravitational acceleration, m/s^2
_CP = 1004.0          # specific heat of dry air, J/(kg K)
_R_DRY = 287.05       # gas constant for dry air, J/(kg K)
_C_TATARSKI = 2.8     # Tatarski proportionality constant c (2.8-3.2)
_PR_T = 1.0           # turbulent Prandtl number (~1 in stable stratification)


def potential_temp_gradient(t_low_c, z_low_m, t_high_c, z_high_m,
                            p_low_hpa=850.0, p_high_hpa=500.0):
    """Potential-temperature gradient Gamma = dTheta/dz (K/m) between two
    pressure levels using their geopotential heights. Positive = stable.

    Theta = T (1000/P)^(R/CP); we difference Theta over the height gap. This is
    the real static-stability gradient Tatarski's C_T^2 needs."""
    if None in (t_low_c, z_low_m, t_high_c, z_high_m):
        return None
    kappa = _R_DRY / _CP
    theta_low = (t_low_c + 273.15) * (1000.0 / p_low_hpa) ** kappa
    theta_high = (t_high_c + 273.15) * (1000.0 / p_high_hpa) ** kappa
    dz = z_high_m - z_low_m
    if dz <= 0:
        return None
    return (theta_high - theta_low) / dz


def _outer_length_scale(gamma, wind_shear_per_s):
    """Outer turbulence length scale L0 (m). In stable stratification L0 is
    buoyancy-limited; we use a shear/buoyancy mixing length, bounded to a
    physically sensible 2-50 m. This is the principal estimated quantity when a
    fine Cn^2 profile is unavailable — documented as such."""
    n2 = (_G / 300.0) * max(gamma, 1e-5)      # buoyancy frequency squared
    if wind_shear_per_s and wind_shear_per_s > 1e-4 and n2 > 0:
        L0 = 0.5 * wind_shear_per_s / n2
    else:
        L0 = 20.0
    return max(2.0, min(50.0, L0))


def calculate_seeing_tatarski(t_850_c, t_500_c, geopot_850_m, geopot_500_m,
                              wind_850_ms=None, wind_250_ms=None,
                              pressure_hpa=850.0, airmass=1.0,
                              wavelength_nm=500.0, layer_thickness_m=500.0):
    """Seeing FWHM (arcsec) from the Tatarski Cn^2 formulation using REAL
    vertical gradients. Returns None if the required profile data is missing.

    Chain (all published, see module header):
      Gamma = dTheta/dz  (from 850/500 hPa T + geopotential heights)
      C_T^2 = (c/Pr_t) L0^(4/3) Gamma^2                    (Tatarski / Basu&Holtslag)
      Cn^2  = (79e-6 P/T^2)^2 C_T^2                        (optical conversion)
      r0    = (0.423 k^2 X integral Cn^2 dh)^(-3/5)        (Fried 1966)
      theta = 0.98 lambda / r0

    HONEST CAVEAT: with only two pressure levels the Cn^2 integral and L0 are
    coarse, so this over-estimates seeing versus a DIMM by a roughly constant
    factor (~1.5x at good sites). Reported uncalibrated — the value is the raw
    physics, not fitted to match published site seeing."""
    gamma = potential_temp_gradient(t_850_c, geopot_850_m, t_500_c, geopot_500_m)
    if gamma is None or gamma <= 0:
        # Non-stable or missing gradient — Tatarski regime doesn't apply.
        return None

    # Free-atmosphere wind shear between 850 hPa and the 250 hPa jet level
    # (~10.4 km), used only to set the mixing length L0.
    shear = None
    if wind_850_ms is not None and wind_250_ms is not None:
        shear = abs(wind_250_ms - wind_850_ms) / max(1.0, 10400.0 - geopot_850_m)

    L0 = _outer_length_scale(gamma, shear)
    ct2 = (_C_TATARSKI / _PR_T) * (L0 ** (4.0 / 3.0)) * (gamma ** 2)

    temp_k = t_850_c + 273.15
    cn2_factor = 79e-6 * pressure_hpa / (temp_k ** 2)
    cn2 = (cn2_factor ** 2) * ct2

    cn2_integral = cn2 * layer_thickness_m
    if cn2_integral <= 0:
        return None

    wavelength_m = wavelength_nm * 1e-9
    k = 2.0 * math.pi / wavelength_m
    r0 = (0.423 * k ** 2 * max(1.0, airmass) * cn2_integral) ** (-3.0 / 5.0)
    theta_arcsec = (0.98 * wavelength_m / r0) * 206265.0
    return round(max(0.3, min(5.0, theta_arcsec)), 2)


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
                     wavelength_nm=500.0,
                     profile=None):
    """
    Estimate atmospheric seeing (FWHM, arcsec).

    PREFERRED PATH: when `profile` (a dict of Open-Meteo pressure-level fields:
    temp_850hpa, temp_500hpa, geopot_850hpa, geopot_500hpa, and optionally
    wind_850hpa, jet_stream_ms) is provided with a stable gradient, seeing is
    computed from the published Tatarski Cn^2 formalism using REAL vertical
    gradients — see calculate_seeing_tatarski / module header.

    FALLBACK PATH (no profile, or non-stable/missing gradient): the original
    surface-weather Fried-parameter heuristic below, which infers Cn^2 from a
    Hufnagel-Valley-style decomposition of surface wind/humidity/altitude.

    Both paths end at the same Fried step:
        θ = 0.98 * λ / r0      (radians)  →  × 206265 → arcsec

    r0 is derived from a Hufnagel–Valley-style Cn² integral
    (see turbulence_integral / fried_parameter). Lower θ = better.
    Exceptional < 0.5, Excellent < 1.0, Good 1.0–1.5,
    Average 1.5–2.5, Poor > 2.5 arcsec.

    temperature_c is retained for signature compatibility and a
    small cold-air stability bonus.
    """
    # PREFERRED: real vertical-gradient Tatarski model when profile data exists.
    if profile:
        t850 = profile.get("temp_850hpa")
        t500 = profile.get("temp_500hpa")
        g850 = profile.get("geopot_850hpa")
        g500 = profile.get("geopot_500hpa")
        # A value is usable only if it is a real, finite number. Missing
        # pressure-level data arrives as None from some paths but as NaN from
        # pandas (a DB NULL), and NaN slips past a plain `None` check --- it then
        # poisons the Tatarski arithmetic and pins the seeing at the 5" ceiling.
        # Require all four to be finite before taking the Tatarski path.
        def _finite(v):
            return v is not None and isinstance(v, (int, float)) and math.isfinite(v)
        if all(_finite(v) for v in (t850, t500, g850, g500)):
            tat = calculate_seeing_tatarski(
                t850, t500, g850, g500,
                wind_850_ms=profile.get("wind_850hpa"),
                wind_250_ms=profile.get("jet_stream_ms"),
                airmass=airmass, wavelength_nm=wavelength_nm)
            if tat is not None:
                return tat
        # else fall through to the surface heuristic below.

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

def _specific_humidity(temp_c, rh_pct, pressure_hpa):
    """Specific humidity q (kg/kg) from temperature, relative humidity and
    pressure, via the Magnus saturation vapour pressure."""
    if None in (temp_c, rh_pct, pressure_hpa) or pressure_hpa <= 0:
        return None
    a, b = 17.625, 243.04
    e_s = 6.112 * math.exp((a * temp_c) / (b + temp_c))   # sat. vapour pressure, hPa
    e = (rh_pct / 100.0) * e_s                            # actual vapour pressure, hPa
    # q = 0.622 e / (P - 0.378 e)
    return 0.622 * e / (pressure_hpa - 0.378 * e)


def calculate_pwv(surface_pressure, humidity_pct,
                  temperature_c, altitude_m=0, profile=None):
    """
    Precipitable Water Vapor (mm). Lower = better for IR/sub-mm work.
    Excellent < 2, Good 2-5, Poor > 10 mm.

    PREFERRED PATH: when `profile` carries relative humidity + temperature at
    pressure levels (rh_850hpa, rh_500hpa, temp_850hpa, temp_500hpa) we integrate
    the standard column relation
        PWV = (1 / (rho_w g)) * integral of q dp
    over surface -> 850 -> 500 hPa (specific humidity q from RH via Magnus).
    This is the physically-correct layered integration used for radiosonde PWV.

    FALLBACK PATH: the previous single-level scale-height approximation.
    """
    # PREFERRED: layered integration over the real humidity profile.
    if profile:
        try:
            rho_w = 1000.0    # water density kg/m^3
            g = 9.80665
            # Build (pressure_hPa, q) nodes from surface up.
            nodes = []
            if None not in (surface_pressure, temperature_c, humidity_pct):
                q0 = _specific_humidity(temperature_c, humidity_pct, surface_pressure)
                if q0 is not None:
                    nodes.append((surface_pressure, q0))
            for p, tk, rk in ((850.0, "temp_850hpa", "rh_850hpa"),
                              (500.0, "temp_500hpa", "rh_500hpa")):
                t = profile.get(tk)
                rh = profile.get(rk)
                if t is not None and rh is not None and p < (surface_pressure or 1e9):
                    q = _specific_humidity(t, rh, p)
                    if q is not None:
                        nodes.append((p, q))
            if len(nodes) >= 2:
                nodes.sort(key=lambda n: -n[0])   # descending pressure (surface first)
                pw_kg_m2 = 0.0                     # column water, kg/m^2
                for (p_lo, q_lo), (p_hi, q_hi) in zip(nodes, nodes[1:]):
                    dp_pa = (p_lo - p_hi) * 100.0  # hPa -> Pa
                    q_mean = 0.5 * (q_lo + q_hi)
                    pw_kg_m2 += q_mean * dp_pa / g
                pwv_mm = pw_kg_m2 / rho_w * 1000.0  # kg/m^2 == mm of water; *1 => mm
                # kg/m^2 of water is already numerically mm; the /rho_w*1000 is identity.
                pwv_mm = pw_kg_m2   # 1 kg/m^2 water column == 1 mm PWV
                if pwv_mm > 0:
                    return round(max(0.1, min(60.0, pwv_mm)), 2)
        except Exception:
            pass   # fall through to heuristic

    if any(v is None for v in [
        surface_pressure, humidity_pct, temperature_c
    ]):
        return None

    # FALLBACK: single-level scale-height approximation.
    a, b = 17.625, 243.04
    svp  = 6.112 * math.exp((a * temperature_c) / (b + temperature_c))
    avp  = (humidity_pct / 100) * svp
    scale_height = 2.0 * math.exp(-altitude_m / 8000)
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

def observing_quality_score(cloud_cover_pct, humidity_pct,
                            wind_speed_ms, precipitation_mm,
                            seeing_arcsec, jet_impact):
    """
    Genuine observing-quality index (0–100), blending the factors that
    actually limit ground-based observing into a single number — in the
    spirit of ClearDarkSky / Meteoblue "astronomy seeing" indices.

    Modelled MULTIPLICATIVELY: any one bad factor drags the whole score
    down, because in real observing a single show-stopper (thick cloud,
    rain, terrible seeing) makes the night unusable regardless of the
    rest. Each sub-factor is a 0–1 transmission-like fraction.

    Factors:
      • clarity      — cloud cover, non-linear (first cloud hurts most)
      • dryness      — humidity (gradual; condensation risk when high)
      • wind_stab    — wind (gradual; vibration/tracking above ~8 m/s)
      • seeing_fac   — atmospheric turbulence (Fried-based seeing)
      • jet_fac      — jet-stream turbulence aloft
      • precip_gate  — hard stop: any real precipitation ⇒ dome closed
    """
    cloud = (cloud_cover_pct if cloud_cover_pct is not None else 0) / 100.0
    rh    = humidity_pct     if humidity_pct     is not None else 50.0
    wind  = wind_speed_ms    if wind_speed_ms    is not None else 0.0
    precip = precipitation_mm if precipitation_mm is not None else 0.0

    # Clarity — non-linear: even light cloud bites hard, heavy cloud
    # asymptotes to unusable. (1-cloud)^1.5 gives a steep early drop.
    clarity = max(0.0, (1.0 - cloud)) ** 1.5

    # Dryness — gentle below 70% RH, falls off toward saturation.
    if rh <= 70:
        dryness = 1.0
    else:
        dryness = max(0.3, 1.0 - (rh - 70) / 60.0)   # 70%→1.0, 100%→0.5

    # Wind stability — fine below ~8 m/s, degrades, poor by ~25 m/s.
    if wind <= 8:
        wind_stab = 1.0
    else:
        wind_stab = max(0.2, 1.0 - (wind - 8) / 25.0)

    # Seeing factor — map arcsec to 0–1 (≤0.7"≈1.0, ~3"≈0.3).
    if seeing_arcsec is None:
        seeing_fac = 0.85           # neutral if unknown
    elif seeing_arcsec <= 0.7:
        seeing_fac = 1.0
    else:
        seeing_fac = max(0.25, 1.0 - (seeing_arcsec - 0.7) / 3.0)

    # Jet-stream factor — turbulence aloft.
    jet_fac = {
        "Negligible": 1.0, "Low": 0.95, "Moderate": 0.85,
        "High": 0.7, "Severe": 0.5, "Unknown": 0.9,
    }.get(jet_impact, 0.9)

    # Precipitation hard gate — any measurable precip closes the dome.
    precip_gate = 1.0 if precip < 0.1 else 0.05

    quality = (clarity * dryness * wind_stab *
               seeing_fac * jet_fac * precip_gate)
    return round(max(0.0, min(1.0, quality)) * 100, 1)


def observing_condition(score):
    if score >= 80:   return "Excellent"
    elif score >= 60: return "Good"
    elif score >= 40: return "Marginal"
    else:             return "Poor"


def get_full_atmospheric_analysis(record):
    """
    Run all three calculations for one observatory record.
    """
    # The record itself carries the pressure-level fields (temp_850hpa, etc.)
    # when available, so pass it as the profile to both calculations — they use
    # the Tatarski/layered-PWV paths if the fields are present, else fall back.
    seeing     = calculate_seeing(
        record.get("temperature_c"),
        record.get("wind_speed_ms"),
        record.get("humidity_pct"),
        record.get("altitude_m", 0),
        profile=record
    )
    pwv        = calculate_pwv(
        record.get("surface_pressure"),
        record.get("humidity_pct"),
        record.get("temperature_c"),
        record.get("altitude_m", 0),
        profile=record
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