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
# formalism, driven by REAL vertical gradients from the Open-Meteo pressure
# levels above the site (850/700/600/500 hPa). Where no profile exists at all, a
# documented fallback combines the ground-layer term with the calibrated median
# free-atmosphere seeing (see calculate_seeing).
_G = 9.80665          # gravitational acceleration, m/s^2
_CP = 1004.0          # specific heat of dry air, J/(kg K)
_R_DRY = 287.05       # gas constant for dry air, J/(kg K)
_C_TATARSKI = 2.8     # Tatarski proportionality constant c (literature 2.1-3.2)
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


def _outer_scale_pow43(wind_shear_per_s):
    """Outer turbulence length scale to the 4/3 power, L0^(4/3) (m^4/3) --- the
    quantity C_T^2 actually needs --- via the Dewan et al. (1993) troposphere
    model:

        L0^(4/3) = 0.1^(4/3) * 10^(1.64 + 42 S)         (S = wind shear, 1/s)

    This is the standard in NWP-derived optical-turbulence work (Dewan 1993;
    Trinquet & Vernin 2007; Masciadri's Astro-Meso-NH forecasts). It is
    dimensionally correct (the earlier shear/N^2 mixing length returned seconds,
    not a length) and takes the shear directly, which is what the 850/250 hPa
    levels provide. Two guards: S is capped at 0.02 1/s (the strong-shear end of
    Dewan's fit) so a spurious wind difference cannot blow up L0^(4/3), and with
    no shear available a representative 3e-3 1/s is used. Shear must be in 1/s
    from winds in m/s."""
    s = wind_shear_per_s if (wind_shear_per_s and wind_shear_per_s > 0) else 3e-3
    # Cap the exponent so a spuriously large shear can't blow up L0^(4/3);
    # 42*S at S~0.02 already gives the strong-shear end of Dewan's fit.
    exponent = 1.64 + 42.0 * min(s, 0.02)
    return (0.1 ** (4.0 / 3.0)) * (10.0 ** exponent)


def _finite(v):
    """A real, finite number (None and NaN are not)."""
    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)


def _boundary_layer_seeing(surface_wind_ms, humidity_pct, altitude_m, airmass):
    """Ground/boundary-layer seeing contribution (arcsec).

    The two pressure levels see only the free atmosphere, but the ground layer
    (lowest ~few hundred m) dominates real seeing at most sites. A MASS/DIMM
    decomposition of the Paranal ASM archive (this repo, tests/) puts the median
    ground layer at ~0.61" -- about two-thirds of the total turbulence variance,
    consistent with the site literature -- so this term is anchored to that
    measurement, NOT to an absolute-elevation scaling.

    Site-dependence:
      * base ~0.77" -- a high, dry site (Paranal-like) STILL has a strong ground
        layer; the previous exp(-h/2500) suppressed it to ~0.2", which the
        MASS/DIMM split shows is far too low.
      * grows with surface wind (shear-driven mechanical mixing);
      * a GENTLE altitude term (scale height 10000 m) -- the ground layer is a
        local surface phenomenon set by topography and heating, only weakly tied
        to absolute elevation, so only the very highest sites see a modest
        reduction.
    (An earlier version also carried a humidity factor; a ranking test against DIMM
    showed it subtracted skill, so it was removed -- see the comment below.)
    Scaled by airmass^0.6 for the slant path. Still a parametrisation, not a
    per-site DIMM fit -- see the honest caveat in calculate_seeing_tatarski."""
    # NaN (a DB NULL via pandas) must count as missing, not slip through and
    # silently pin the term at its 0.15" floor.
    w = surface_wind_ms if _finite(surface_wind_ms) else 4.0
    h = altitude_m if _finite(altitude_m) else 0.0
    # Base ground-layer seeing (arcsec), anchored so Paranal (2635 m) at its
    # MEDIAN surface conditions (~2.8 m/s 10 m wind) reproduces the per-timestamp
    # MASS/DIMM-measured ground-layer median of 0.61" (2026-05..08, ~32k pairs).
    #
    # An earlier version multiplied in a humidity factor 1 + max(0, RH-40)/150 as a
    # rough surface-instability proxy. A ranking test against DIMM showed it
    # subtracted skill (eps_bl alone rose from +0.28 to +0.33 without it, and the
    # full-model rho rose +0.34 -> +0.36), consistent with humidity's link to
    # OPTICAL turbulence being weak; it was removed. (The Paranal anchor is
    # unaffected: at its median RH ~26% the old factor was already 1.0.)
    base = 0.77
    wind_term = (1.0 + (w / 8.0) ** 2) ** 0.3          # more wind -> more shear
    alt_term = math.exp(-h / 10000.0)                  # gentle: local, not elev.
    theta_bl = base * wind_term * alt_term
    theta_bl *= max(1.0, airmass) ** 0.6               # slant path
    return max(0.15, theta_bl)


def _layer_cn2(t_lo_c, p_lo, z_lo, t_hi_c, p_hi, z_hi, shear):
    """Refractive-index structure constant C_n^2 (m^-2/3) for the layer between
    two pressure levels, via the Tatarski chain:
        Gamma = dTheta/dz, C_T^2 = c/Pr_t * L0^4/3 * (T/Theta)^2 * Gamma^2,
        C_n^2 = (79e-6 P/T^2)^2 C_T^2
    Uses the layer-mean T, P and Theta. Returns 0.0 for a non-stable/degenerate
    layer (those contribute no turbulence integral). `shear` is the wind shear
    across THIS layer (1/s), used for the Dewan L0."""
    kappa = _R_DRY / _CP
    th_lo = (t_lo_c + 273.15) * (1000.0 / p_lo) ** kappa
    th_hi = (t_hi_c + 273.15) * (1000.0 / p_hi) ** kappa
    dz = z_hi - z_lo
    if dz <= 0:
        return 0.0
    gamma = (th_hi - th_lo) / dz
    if gamma <= 0:                       # unstable/neutral: no Tatarski turbulence
        return 0.0
    l0_pow43 = _outer_scale_pow43(shear)
    t_mean = 0.5 * ((t_lo_c + 273.15) + (t_hi_c + 273.15))
    theta_mean = 0.5 * (th_lo + th_hi)
    p_mean = 0.5 * (p_lo + p_hi)
    t_over_theta_sq = (t_mean / theta_mean) ** 2
    ct2 = (_C_TATARSKI / _PR_T) * l0_pow43 * t_over_theta_sq * (gamma ** 2)
    cn2_factor = 79e-6 * p_mean / (t_mean ** 2)
    return (cn2_factor ** 2) * ct2


# Free-atmosphere calibration constants (Paranal, against ESO MASS).
#
# Each is set so the model's free-atmosphere median over the MASS-matched hours
# of 2026-05..08 equals the MASS median over the same hours; calibrate() in
# tests/hindcast_multiyear.py re-derives them.
#
# _MULTILEVEL_CN2_SCALE (C) scales the per-level C_n^2 integral. It is degenerate
# with the Tatarski coefficient c, so only c_eff = c*C is identifiable. With all
# winds correctly in m/s, C ~ 2 and c_eff ~ 5.7 -- roughly twice the published
# 2.1-3.2 range. We read that as the coarse pressure levels under-resolving the
# thin, sharp gradients and shears that carry real optical turbulence, a factor
# the calibration absorbs. (An earlier C = 0.77, c_eff = 2.16, was an artefact of
# calibrating on pressure-level winds left in km/h, which inflated the shear.)
_MULTILEVEL_CN2_SCALE = 2.03
# Two-level fallback (850->500 hPa only): effective turbulent-layer thickness.
_FALLBACK_THICKNESS_M = 4900.0
# No-profile fallback: the calibrated median free-atmosphere seeing (zenith).
_FREE_ATM_MEDIAN_ARCSEC = 0.45


def free_atmosphere_seeing_multilevel(levels, altitude_m, airmass=1.0,
                                      wavelength_nm=500.0,
                                      cn2_scale=_MULTILEVEL_CN2_SCALE):
    """Free-atmosphere seeing (arcsec) by integrating C_n^2 over the REAL
    pressure levels that lie ABOVE the site --- the per-level integration that
    removes the single-slab effective-thickness parameter.

    `levels` is a list of dicts, each {'p': hPa, 't': degC, 'z': geopot m,
    'w': wind m/s (optional)}, in any order. We:
      1. sort by height,
      2. drop levels at or below the site, but interpolate the lowest bracket
         straddling the site up to the site elevation (so the integral starts
         exactly at the telescope, not at the nearest level below it),
      3. for each adjacent pair, form C_n^2 (its own Gamma, its own Dewan shear)
         and multiply by that pair's GEOMETRIC depth dz --- so each layer carries
         its true thickness rather than a shared assumed one,
      4. sum to get integral C_n^2 dh, then Fried r0 and eps = 0.98 lambda/r0.

    For a site BELOW the lowest level (850 hPa, ~1500 m) there is no bracket to
    interpolate, so the integral starts at 850 hPa; the slab between the
    telescope and that level is left to the ground-layer term.

    Returns None if fewer than two usable levels remain above the site."""
    usable = [L for L in levels
              if L.get("t") is not None and L.get("z") is not None
              and L.get("p")]
    if len(usable) < 2:
        return None
    usable.sort(key=lambda L: L["z"])

    h_site = altitude_m if altitude_m is not None else 0.0

    # Keep levels above the site; interpolate the straddling bracket to h_site.
    nodes = [L for L in usable if L["z"] > h_site]
    below = [L for L in usable if L["z"] <= h_site]
    if below and nodes:
        lo, hi = below[-1], nodes[0]        # bracket straddling the site
        frac = (h_site - lo["z"]) / (hi["z"] - lo["z"])
        # log-linear interpolation of pressure, linear for T and wind
        p_site = lo["p"] * (hi["p"] / lo["p"]) ** frac
        t_site = lo["t"] + frac * (hi["t"] - lo["t"])
        w_lo, w_hi = lo.get("w"), hi.get("w")
        w_site = (w_lo + frac * (w_hi - w_lo)
                  if (w_lo is not None and w_hi is not None) else hi.get("w"))
        nodes = [{"p": p_site, "t": t_site, "z": h_site, "w": w_site}] + nodes
    if len(nodes) < 2:
        return None

    cn2_integral = 0.0
    for lo, hi in zip(nodes, nodes[1:]):
        dz = hi["z"] - lo["z"]
        if dz <= 0:
            continue
        w_lo, w_hi = lo.get("w"), hi.get("w")
        shear = (abs(w_hi - w_lo) / dz
                 if (w_lo is not None and w_hi is not None) else None)
        cn2 = _layer_cn2(lo["t"], lo["p"], lo["z"],
                         hi["t"], hi["p"], hi["z"], shear)
        cn2_integral += cn2 * dz           # each layer, its own geometric depth

    if cn2_integral <= 0:
        return None
    cn2_integral *= cn2_scale               # calibration to measured MASS (see const)
    wavelength_m = wavelength_nm * 1e-9
    k = 2.0 * math.pi / wavelength_m
    r0 = (0.423 * k ** 2 * max(1.0, airmass) * cn2_integral) ** (-3.0 / 5.0)
    return (0.98 * wavelength_m / r0) * 206265.0


def calculate_seeing_tatarski(t_850_c, t_500_c, geopot_850_m, geopot_500_m,
                              wind_850_ms=None, wind_250_ms=None,
                              wind_500_ms=None,
                              pressure_hpa=850.0, airmass=1.0,
                              wavelength_nm=500.0,
                              layer_thickness_m=None,
                              surface_wind_ms=None, humidity_pct=None,
                              altitude_m=None, levels=None,
                              cn2_scale=None,
                              components=False):
    """Seeing FWHM (arcsec) from the Tatarski Cn^2 formulation using REAL
    vertical gradients, combined in quadrature with the ground-layer term.
    Returns None if the required profile data is missing. All winds in m/s.

    Chain (all published, see module header):
      Gamma = dTheta/dz  (per layer between the levels above the site)
      C_T^2 = (c/Pr_t) L0^(4/3) (T/Theta)^2 Gamma^2         (Tatarski / Basu&Holtslag)
      Cn^2  = (79e-6 P/T^2)^2 C_T^2                        (optical conversion)
      r0    = (0.423 k^2 X integral Cn^2 dh)^(-3/5)        (Fried 1966)
      eps   = 0.98 lambda / r0

    The (T/Theta)^2 factor converts the potential-temperature structure constant
    (C_theta^2, which the dTheta/dz mixing-length argument yields) to the
    actual-temperature one C_T^2 that the optical conversion acts on.

    PREFERRED free-atmosphere path: the per-level integration over `levels`
    (850/700/600/500 hPa) above the site. FALLBACK: a single 850->500 hPa
    gradient over an effective layer thickness, used only when the per-level
    path is unavailable. Both free-atmosphere constants are calibrated to the
    MASS median at Paranal (see the constants above).

    components=True returns {"total", "free", "ground"} instead of a number."""
    if cn2_scale is None:
        cn2_scale = _MULTILEVEL_CN2_SCALE
    if layer_thickness_m is None:
        layer_thickness_m = _FALLBACK_THICKNESS_M

    theta_free = None
    if levels:
        theta_free = free_atmosphere_seeing_multilevel(
            levels, altitude_m, airmass=airmass, wavelength_nm=wavelength_nm,
            cn2_scale=cn2_scale)

    if theta_free is None:
        # Two-level fallback: needs a stable 850->500 hPa gradient.
        gamma = potential_temp_gradient(t_850_c, geopot_850_m, t_500_c, geopot_500_m)
        if gamma is None or gamma <= 0:
            return None
        # Dewan shear over the same 850->500 layer as Gamma (850->250 only if
        # the 500 hPa wind is missing).
        shear = None
        if wind_850_ms is not None and wind_500_ms is not None:
            shear = abs(wind_500_ms - wind_850_ms) / max(1.0, geopot_500_m - geopot_850_m)
        elif wind_850_ms is not None and wind_250_ms is not None:
            shear = abs(wind_250_ms - wind_850_ms) / max(1.0, 10400.0 - geopot_850_m)
        kappa = _R_DRY / _CP
        theta_850 = (t_850_c + 273.15) * (1000.0 / 850.0) ** kappa
        theta_500 = (t_500_c + 273.15) * (1000.0 / 500.0) ** kappa
        t_mean = 0.5 * ((t_850_c + 273.15) + (t_500_c + 273.15))
        t_over_theta_sq = (t_mean / (0.5 * (theta_850 + theta_500))) ** 2
        ct2 = (_C_TATARSKI / _PR_T) * _outer_scale_pow43(shear) \
            * t_over_theta_sq * (gamma ** 2)
        cn2 = (79e-6 * pressure_hpa / (t_850_c + 273.15) ** 2) ** 2 * ct2
        cn2_integral = cn2 * layer_thickness_m
        if cn2_integral <= 0:
            return None
        wavelength_m = wavelength_nm * 1e-9
        k = 2.0 * math.pi / wavelength_m
        r0 = (0.423 * k ** 2 * max(1.0, airmass) * cn2_integral) ** (-3.0 / 5.0)
        theta_free = (0.98 * wavelength_m / r0) * 206265.0

    # Total = free atmosphere and ground layer in quadrature (independent
    # turbulent layers). The pressure levels resolve only the free atmosphere;
    # the ground layer carries ~2/3 of the seeing variance (MASS/DIMM, Paranal).
    theta_ground = _boundary_layer_seeing(
        surface_wind_ms, humidity_pct, altitude_m, airmass)
    total = round(max(0.3, min(5.0, math.sqrt(theta_free ** 2 + theta_ground ** 2))), 2)
    if components:
        return {"total": total, "free": theta_free, "ground": theta_ground}
    return total


def calculate_seeing(temperature_c, wind_speed_ms,
                     humidity_pct, altitude_m=0,
                     airmass=1.0,
                     wavelength_nm=500.0,
                     profile=None):
    """
    Estimate atmospheric seeing (FWHM, arcsec) at 500 nm.

    PREFERRED PATH: `profile` holds the Open-Meteo pressure-level fields of a
    weather record (see profile_from_record): temp/geopot/wind at 850, 700,
    600 and 500 hPa. Seeing is then the per-level Tatarski free atmosphere plus
    the ground-layer term (calculate_seeing_tatarski).

    FALLBACK (no usable profile): the same ground-layer term combined in
    quadrature with the calibrated median free-atmosphere seeing. This keeps
    the site's surface-wind and altitude dependence without a free-atmosphere
    forecast; it is indicative only.

    Exceptional < 0.5, Excellent < 1.0, Good 1.0-1.5,
    Average 1.5-2.5, Poor > 2.5 arcsec.
    """
    if profile is not None:
        t850 = profile.get("temp_850hpa")
        t500 = profile.get("temp_500hpa")
        g850 = profile.get("geopot_850hpa")
        g500 = profile.get("geopot_500hpa")
        if all(_finite(v) for v in (t850, t500, g850, g500)):
            # The integral uses 850-500 hPa only (250 hPa supplies the jet wind,
            # never a layer), matching the model validated in the paper.
            levels = []
            for p, tk, zk, wk in (
                    (850.0, "temp_850hpa", "geopot_850hpa", "wind_850hpa"),
                    (700.0, "temp_700hpa", "geopot_700hpa", "wind_700hpa"),
                    (600.0, "temp_600hpa", "geopot_600hpa", "wind_600hpa"),
                    (500.0, "temp_500hpa", "geopot_500hpa", "wind_500hpa")):
                tv, zv = profile.get(tk), profile.get(zk)
                if _finite(tv) and _finite(zv):
                    wv = profile.get(wk)
                    levels.append({"p": p, "t": tv, "z": zv,
                                   "w": wv if _finite(wv) else None})

            def fin(k):
                v = profile.get(k)
                return v if _finite(v) else None
            tat = calculate_seeing_tatarski(
                t850, t500, g850, g500,
                wind_850_ms=fin("wind_850hpa"), wind_250_ms=fin("jet_stream_ms"),
                wind_500_ms=fin("wind_500hpa"),
                airmass=airmass, wavelength_nm=wavelength_nm,
                surface_wind_ms=wind_speed_ms, humidity_pct=humidity_pct,
                altitude_m=altitude_m,
                levels=levels if len(levels) >= 2 else None)
            if tat is not None:
                return tat

    if not _finite(wind_speed_ms) and not _finite(altitude_m):
        return None
    free = _FREE_ATM_MEDIAN_ARCSEC * max(1.0, airmass) ** 0.6
    ground = _boundary_layer_seeing(wind_speed_ms, humidity_pct, altitude_m, airmass)
    return round(max(0.3, min(5.0, math.sqrt(free ** 2 + ground ** 2))), 2)


PROFILE_FIELDS = (
    "temp_850hpa", "temp_700hpa", "temp_600hpa", "temp_500hpa",
    "geopot_850hpa", "geopot_700hpa", "geopot_600hpa", "geopot_500hpa",
    "wind_850hpa", "wind_700hpa", "wind_600hpa", "wind_500hpa",
    "jet_stream_ms", "rh_850hpa", "rh_500hpa", "pwv_column", "model_elevation_m")


def profile_from_record(record):
    """The pressure-level profile dict calculate_seeing / calculate_pwv expect,
    built from a weather record (DB row dict or pandas Series). Every caller
    should pass this so the live site and API run the model in the paper."""
    return {k: record.get(k) for k in PROFILE_FIELDS}


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
    # MOST PREFERRED: the model's own total-column PWV (Open-Meteo), corrected to
    # the site altitude. This is a proper radiative-transfer product and far more
    # reliable than deriving PWV from 2-3 coarse humidity nodes.
    #
    # IMPORTANT: Open-Meteo integrates the column from the MODEL GRID CELL's
    # terrain surface, not from sea level. That terrain height (the "elevation"
    # field, stored as model_elevation_m) is usually within ~100 m of the site, so
    # only the residual water between the model terrain and the telescope must be
    # removed: PWV(site) = PWV_model * exp(-(h_site - h_model)/H_w), H_w ~ 2000 m.
    # (An earlier version scaled from sea level, exp(-h_site/H_w), which removed the
    # sub-site column a SECOND time and biased PWV ~3x low, worsening with altitude
    # across the whole catalogue -- see the LHATPRO validation in the paper.)
    if profile is not None:
        pwv_col = profile.get("pwv_column")
        if pwv_col is not None and pwv_col >= 0:
            h_site = altitude_m or 0.0
            h_model = profile.get("model_elevation_m")
            if not _finite(h_model):
                # Without the model terrain height, assume the cell already sits
                # near the site (true for the targeted-coordinate query) and apply
                # no double correction. A small residual default guards low sites.
                dz = 0.0
            else:
                dz = max(0.0, h_site - h_model)
            pwv_site = pwv_col * math.exp(-dz / 2000.0)
            return round(max(0.1, min(60.0, pwv_site)), 2)

    # PREFERRED (fallback): layered integration over the humidity profile.
    if profile is not None:
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
                    # Specific humidity falls ~exponentially with height, so over
                    # a wide pressure gap the arithmetic mean over-weights the
                    # moist lower node and over-counts water (a linear mean gave
                    # PWV ~3x high vs measured). Integrate assuming exponential
                    # decay between nodes: the layer-mean q is then the
                    # logarithmic (geometric-integral) mean, (q_lo - q_hi)/ln(q_lo/q_hi).
                    if q_lo > 0 and q_hi > 0 and abs(q_lo - q_hi) > 1e-9:
                        q_mean = (q_lo - q_hi) / math.log(q_lo / q_hi)
                    else:
                        q_mean = 0.5 * (q_lo + q_hi)
                    pw_kg_m2 += q_mean * dp_pa / g
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
                            seeing_arcsec, jet_impact,
                            temperature_c=None, dewpoint_c=None):
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
      • dew_fac      — dew-point depression (temp - dewpoint): a
                       DISTINCT condensation risk from relative humidity.
                       Two nights can share the same RH but very different
                       dew margins if the air temperature itself differs;
                       RH alone can miss a close approach to the dew
                       point. Optional (temperature_c/dewpoint_c) --
                       neutral (1.0) when either is unavailable, so this
                       does not change the score for existing callers
                       that don't yet supply them.
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

    # Dew-point depression (temp - dewpoint) — condensation risk that RH
    # alone can miss: two nights at the same RH can sit at very different
    # distances from saturation depending on air temperature. Fine above
    # ~3 degC margin, sharp penalty as the margin closes toward 0 degC
    # (condensation onset on optics near the dew point itself). Neutral
    # (1.0) whenever either input is missing, so callers that don't yet
    # supply temperature_c/dewpoint_c are unaffected.
    if temperature_c is None or dewpoint_c is None:
        dew_fac = 1.0
    else:
        dew_margin = temperature_c - dewpoint_c
        if dew_margin >= 3.0:
            dew_fac = 1.0
        elif dew_margin <= 0.0:
            dew_fac = 0.2                            # at/below dew point
        else:
            dew_fac = 0.2 + 0.8 * (dew_margin / 3.0)  # 0degC->0.2, 3degC->1.0

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

    quality = (clarity * dryness * dew_fac * wind_stab *
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