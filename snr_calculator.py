import math

# ── Telescope database ────────────────────────────────────────────
TELESCOPE_SPECS = {
    "default": {
        "name":               "1.0m default",
        "aperture_m":         1.0,
        "focal_ratio":        8.0,
        "pixel_scale":        0.5,
        "read_noise":         5.0,
        "dark_current":       0.001,
        "quantum_efficiency": 0.85,
        "throughput":         0.75,
        "obstruction":        0.30,
        "full_well_e":        100000,
        "type":               "optical"
    },
    "Paranal Observatory": {
        "name":               "VLT (8.2m)",
        "aperture_m":         8.2,
        "focal_ratio":        13.4,
        "pixel_scale":        0.126,
        "read_noise":         2.9,
        "dark_current":       0.0005,
        "quantum_efficiency": 0.92,
        "throughput":         0.80,
        "obstruction":        0.14,
        "full_well_e":        200000,
        "type":               "optical"
    },
    "Mauna Kea Observatory": {
        "name":               "Keck (10m)",
        "aperture_m":         10.0,
        "focal_ratio":        15.0,
        "pixel_scale":        0.18,
        "read_noise":         3.5,
        "dark_current":       0.001,
        "quantum_efficiency": 0.90,
        "throughput":         0.78,
        "type":               "optical"
    },
    "Subaru Telescope": {
        "name":               "Subaru (8.2m)",
        "aperture_m":         8.2,
        "focal_ratio":        12.2,
        "pixel_scale":        0.202,
        "read_noise":         4.5,
        "dark_current":       0.001,
        "quantum_efficiency": 0.88,
        "throughput":         0.76,
        "type":               "optical"
    },
    "La Palma Observatory": {
        "name":               "GTC (10.4m)",
        "aperture_m":         10.4,
        "focal_ratio":        17.0,
        "pixel_scale":        0.127,
        "read_noise":         4.0,
        "dark_current":       0.001,
        "quantum_efficiency": 0.91,
        "throughput":         0.79,
        "type":               "optical"
    },
    "Atacama Large Millimeter Array": {
        "name":               "ALMA (Array)",
        "aperture_m":         12.0,
        "focal_ratio":        8.0,
        "pixel_scale":        1.0,
        "read_noise":         0.1,
        "dark_current":       0.0001,
        "quantum_efficiency": 0.95,
        "throughput":         0.70,
        "type":               "radio"
    }
}

def get_telescope_specs(observatory_name, altitude_m=0):
    """
    Get telescope specs for an observatory.
    Falls back to estimating based on altitude.
    """
    if observatory_name in TELESCOPE_SPECS:
        return TELESCOPE_SPECS[observatory_name]

    # Estimate aperture based on altitude
    if altitude_m > 4000:
        aperture = 8.0
    elif altitude_m > 2500:
        aperture = 4.0
    elif altitude_m > 1500:
        aperture = 2.5
    elif altitude_m > 500:
        aperture = 1.5
    else:
        aperture = 1.0

    # Pixel scale scales with aperture
    pixel_scale = max(0.15, 0.5 / aperture)

    return {
        "name":               f"{aperture}m estimated",
        "aperture_m":         aperture,
        "focal_ratio":        8.0,
        "pixel_scale":        pixel_scale,
        "read_noise":         5.0,
        "dark_current":       0.001,
        "quantum_efficiency": 0.85,
        "throughput":         0.75,
        "type":               "optical"
    }

# ── Standard photometric filters ──────────────────────────────────
# Johnson-Cousins broadband system plus common narrowband filters.
# These are universal definitions (same at every observatory) —
# centre wavelength and bandwidth in nanometres, plus the band key
# used for site-altitude-dependent atmospheric extinction.
PHOTOMETRIC_FILTERS = {
    "U (ultraviolet)":  {"wavelength_nm": 365,  "bandwidth_nm": 66,  "band": "U"},
    "B (blue)":         {"wavelength_nm": 445,  "bandwidth_nm": 94,  "band": "B"},
    "V (visual)":       {"wavelength_nm": 551,  "bandwidth_nm": 88,  "band": "V"},
    "R (red)":          {"wavelength_nm": 658,  "bandwidth_nm": 138, "band": "R"},
    "I (near-IR)":      {"wavelength_nm": 806,  "bandwidth_nm": 149, "band": "I"},
    "Hα (narrowband)":  {"wavelength_nm": 656,  "bandwidth_nm": 3,   "band": "R"},
    "OIII (narrowband)":{"wavelength_nm": 501,  "bandwidth_nm": 3,   "band": "V"},
}

# ── Sky background by moon phase ──────────────────────────────────
SKY_BRIGHTNESS = {
    "new_moon":  22.0,
    "crescent":  21.5,
    "quarter":   20.5,
    "gibbous":   19.0,
    "full_moon": 17.5
}

# ── Object magnitudes ─────────────────────────────────────────────
OBJECT_MAGNITUDES = {
    # Planets
    "Mercury":   -1.0,
    "Venus":     -4.5,
    "Mars":      -2.0,
    "Jupiter":   -2.5,
    "Saturn":     0.5,
    "Uranus":     5.7,
    "Neptune":    8.0,
    # Messier objects
    "M1 — Crab Nebula":          8.4,
    "M2 — Globular Cluster":     6.5,
    "M3 — Globular Cluster":     6.2,
    "M4 — Globular Cluster":     5.9,
    "M5 — Globular Cluster":     5.8,
    "M8 — Lagoon Nebula":        5.8,
    "M13 — Hercules Cluster":    5.8,
    "M16 — Eagle Nebula":        6.4,
    "M17 — Omega Nebula":        6.0,
    "M20 — Trifid Nebula":       8.5,
    "M27 — Dumbbell Nebula":     7.5,
    "M31 — Andromeda Galaxy":    3.4,
    "M33 — Triangulum Galaxy":   5.7,
    "M42 — Orion Nebula":        4.0,
    "M45 — Pleiades":            1.6,
    "M51 — Whirlpool Galaxy":    8.4,
    "M57 — Ring Nebula":         8.8,
    "M63 — Sunflower Galaxy":    8.6,
    "M64 — Black Eye Galaxy":    8.5,
    "M81 — Bode's Galaxy":       6.9,
    "M82 — Cigar Galaxy":        8.4,
    "M87 — Virgo A Galaxy":      8.6,
    "M97 — Owl Nebula":          8.9,
    "M101 — Pinwheel Galaxy":    7.9,
    "M104 — Sombrero Galaxy":    8.0,
    # NGC objects
    "NGC 224 — Andromeda Core":     3.4,
    "NGC 5139 — Omega Centauri":    3.9,
    "NGC 869 — Double Cluster h":   5.3,
    "NGC 884 — Double Cluster Chi": 6.1,
    "NGC 7293 — Helix Nebula":      7.3,
    "NGC 3372 — Eta Carinae Neb":   1.0,
    "NGC 5128 — Centaurus A":       6.8,
    "NGC 7000 — North America Neb": 4.0,
    "NGC 2070 — Tarantula Nebula":  8.0,
    "NGC 2244 — Rosette Nebula":    6.0,
    # Famous stars
    "Sirius":     -1.46,
    "Canopus":    -0.72,
    "Arcturus":   -0.05,
    "Vega":        0.03,
    "Capella":     0.08,
    "Rigel":       0.13,
    "Betelgeuse":  0.50,
    "Polaris":     1.98,
    "Antares":     1.09,
    "Aldebaran":   0.87,
    "Spica":       0.98,
    "Fomalhaut":   1.16,
    "Deneb":       1.25,
    # Special
    "Galactic Centre": 4.5,
}

# ── Angular sizes for extended objects (arcminutes) ───────────────
OBJECT_ANGULAR_SIZES = {
    "M1 — Crab Nebula":             7.0,
    "M8 — Lagoon Nebula":           90.0,
    "M16 — Eagle Nebula":           35.0,
    "M17 — Omega Nebula":           46.0,
    "M20 — Trifid Nebula":          28.0,
    "M27 — Dumbbell Nebula":        8.0,
    "M31 — Andromeda Galaxy":       178.0,
    "M33 — Triangulum Galaxy":      70.0,
    "M42 — Orion Nebula":           85.0,
    "M45 — Pleiades":               110.0,
    "M51 — Whirlpool Galaxy":       11.0,
    "M57 — Ring Nebula":            1.4,
    "M63 — Sunflower Galaxy":       12.6,
    "M64 — Black Eye Galaxy":       10.0,
    "M81 — Bode's Galaxy":          26.9,
    "M82 — Cigar Galaxy":           14.0,
    "M87 — Virgo A Galaxy":         8.3,
    "M97 — Owl Nebula":             3.4,
    "M101 — Pinwheel Galaxy":       28.8,
    "M104 — Sombrero Galaxy":       8.7,
    "NGC 224 — Andromeda Core":     178.0,
    "NGC 5139 — Omega Centauri":    36.0,
    "NGC 869 — Double Cluster h":   30.0,
    "NGC 884 — Double Cluster Chi": 30.0,
    "NGC 7293 — Helix Nebula":      16.0,
    "NGC 3372 — Eta Carinae Neb":   120.0,
    "NGC 5128 — Centaurus A":       25.7,
    "NGC 7000 — North America Neb": 120.0,
    "NGC 2070 — Tarantula Nebula":  40.0,
    "NGC 2244 — Rosette Nebula":    80.0,
    "Sirius":      0.0,
    "Canopus":     0.0,
    "Arcturus":    0.0,
    "Vega":        0.0,
    "Rigel":       0.0,
    "Betelgeuse":  0.056,
    "Polaris":     0.0,
    "Antares":     0.046,
}

# ── Sky brightness: Krisciunas & Schaefer (1991) moon model ───────
def _mag_to_nanolambert(mag_arcsec2):
    """V-band surface brightness (mag/arcsec^2) -> luminance in nanoLamberts,
    per Krisciunas & Schaefer (1991) Eq. 27."""
    return 34.08 * math.exp(20.7233 - 0.92104 * mag_arcsec2)


def _nanolambert_to_mag(b_nl):
    """NanoLamberts -> V-band surface brightness (mag/arcsec^2), the inverse of
    _mag_to_nanolambert (K&S 1991 Eq. 28)."""
    if b_nl <= 0:
        return 22.0
    return (20.7233 - math.log(b_nl / 34.08)) / 0.92104


def moon_sky_brightness(moon_phase_pct, moon_alt_deg, target_alt_deg,
                        moon_target_sep_deg, dark_sky_mag=21.8,
                        k_extinction=0.15):
    """V-band sky brightness (mag/arcsec^2) including moonlight, via the
    Krisciunas & Schaefer (1991) model (PASP 103, 1033).

    Adds the Moon's scattered-light contribution to a dark-sky baseline as a
    function of lunar phase, the Moon's and target's airmasses, and the angular
    separation between them. Larger separation and lower Moon => darker sky.
    Below the horizon the Moon contributes nothing.

    Parameters
    ----------
    moon_phase_pct : illuminated fraction (0-100).
    moon_alt_deg, target_alt_deg : altitudes above the horizon (deg).
    moon_target_sep_deg : Moon-target angular separation (deg).
    dark_sky_mag : moonless zenith sky brightness (mag/arcsec^2); site darkness.
    k_extinction : V-band atmospheric extinction coefficient (mag/airmass).
    """
    # No Moon contribution when it is below the horizon.
    if moon_alt_deg is None or moon_alt_deg <= 0:
        return round(dark_sky_mag, 2)
    if target_alt_deg is None or target_alt_deg <= 0:
        return round(dark_sky_mag, 2)
    rho = max(1.0, min(179.0, moon_target_sep_deg or 60.0))

    # Lunar phase angle alpha (deg): 0 = full, 180 = new.
    alpha = (1.0 - (moon_phase_pct or 0) / 100.0) * 180.0
    # Illuminance of the Moon outside the atmosphere (K&S Eq. 20). The +16.57
    # zero-point puts i_star on the scale that makes f(rho)*i_star come out in
    # nanoLamberts directly (K&S 1991).
    m_star = -12.73 + 0.026 * abs(alpha) + 4e-9 * alpha ** 4
    i_star = 10 ** (-0.4 * (m_star + 16.57))

    # Scattering function f(rho): Rayleigh + Mie/aureole terms (K&S Eq. 21).
    f_rho = (10 ** 5.36) * (1.06 + math.cos(math.radians(rho)) ** 2) \
        + 10 ** (6.15 - rho / 40.0)

    # Airmass along a line of sight at altitude h (K&S Eq. 3).
    def _X(h):
        z = 90.0 - h
        return (1.0 - 0.96 * math.sin(math.radians(z)) ** 2) ** -0.5

    X_moon = _X(moon_alt_deg)
    X_target = _X(target_alt_deg)

    # Moon's added brightness in nanoLamberts (K&S Eq. 15).
    b_moon = (f_rho * i_star
              * 10 ** (-0.4 * k_extinction * X_moon)
              * (1.0 - 10 ** (-0.4 * k_extinction * X_target)))

    # Dark sky in nanoLamberts, then add the Moon and convert back to mag.
    b_dark = _mag_to_nanolambert(dark_sky_mag)
    b_total = b_dark + max(0.0, b_moon)
    return round(_nanolambert_to_mag(b_total), 2)


def get_sky_brightness(moon_phase_pct, moon_altitude_deg,
                       target_altitude_deg=None, moon_target_sep_deg=None,
                       dark_sky_mag=21.8, k_extinction=0.15):
    """Sky brightness (V mag/arcsec^2).

    If the Moon-target separation and target altitude are provided, use the
    physical Krisciunas & Schaefer (1991) model (separation is the dominant
    driver of moonlit sky brightness). Otherwise fall back to the original
    phase/altitude lookup so existing callers are unchanged.
    """
    if (target_altitude_deg is not None and moon_target_sep_deg is not None):
        return moon_sky_brightness(
            moon_phase_pct, moon_altitude_deg, target_altitude_deg,
            moon_target_sep_deg, dark_sky_mag=dark_sky_mag,
            k_extinction=k_extinction)

    # ── Legacy fallback: 5-bucket phase table + linear altitude term ──
    if moon_altitude_deg <= 0:
        return SKY_BRIGHTNESS["new_moon"]
    if moon_phase_pct < 10:
        base = SKY_BRIGHTNESS["new_moon"]
    elif moon_phase_pct < 35:
        base = SKY_BRIGHTNESS["crescent"]
    elif moon_phase_pct < 60:
        base = SKY_BRIGHTNESS["quarter"]
    elif moon_phase_pct < 85:
        base = SKY_BRIGHTNESS["gibbous"]
    else:
        base = SKY_BRIGHTNESS["full_moon"]
    alt_factor = moon_altitude_deg / 90
    return round(max(17.0, base - (alt_factor * 2.0)), 2)

# Secondary (colour-dependent) extinction coefficients k2 (mag/airmass per unit
# colour), by band. The bluer the star, the more its light is scattered per
# airmass, so extinction depends weakly on colour: k(colour) = k1 + k2*(B-V).
# k2 is largest in the blue (Rayleigh scattering ~ lambda^-4) and negligible in
# the red/IR. Representative values (small; e.g. Hardie 1962 for La Palma-like
# sites). Applied only when a target colour is supplied.
SECONDARY_EXTINCTION_K2 = {
    "U": -0.05, "B": -0.03, "V": -0.01, "R": 0.00, "I": 0.00,
    "J": 0.00, "H": 0.00, "K": 0.00,
}

# Colour terms for the instrumental->standard transformation: the observer's
# filter response differs slightly from the standard system, so the calibrated
# magnitude picks up a term proportional to the star's colour,
# m_std = m_inst + zp + colour_term*(B-V). Small, band-dependent. Applied for
# reporting when a colour is known; the sign/scale follow standard UBVRI
# transformations (e.g. Bessell 1990). Not used inside the SNR itself.
COLOUR_TERM = {
    "U": 0.03, "B": 0.06, "V": -0.03, "R": -0.02, "I": -0.02,
    "J": 0.00, "H": 0.00, "K": 0.00,
}


def atmospheric_extinction(altitude_deg,
                           extinction_coeff=None,
                           site_altitude_m=2000.0,
                           filter_band="V",
                           colour_bv=None):
    """Atmospheric transmission fraction toward a target.

    If `colour_bv` (the star's B-V) is given, the extinction coefficient
    includes the secondary, colour-dependent term k = k1 + k2*(B-V) --- bluer
    stars are extinguished slightly more per airmass (Rayleigh scattering). With
    no colour, only the primary coefficient k1 is used, exactly as before.
    """
    if altitude_deg is None or altitude_deg <= 0:
        return 0.5
    if altitude_deg >= 90:
        airmass = 1.0
    elif altitude_deg < 1:
        airmass = 40.0
    else:
        airmass = 1 / math.sin(math.radians(altitude_deg))

    # Primary (colour-independent) coefficient.
    if extinction_coeff is None:
        from airmass_calculator import extinction_coefficient
        extinction_coeff = extinction_coefficient(
            site_altitude_m, filter_band)

    # Secondary (colour-dependent) term, when a target colour is available.
    if colour_bv is not None:
        k2 = SECONDARY_EXTINCTION_K2.get(filter_band, 0.0)
        extinction_coeff = extinction_coeff + k2 * colour_bv

    extinction_mag = extinction_coeff * airmass
    transmission   = 10 ** (-extinction_mag / 2.5)
    return round(min(1.0, max(0.0, transmission)), 4)


def colour_correction(filter_band, colour_bv):
    """Instrumental->standard colour term: the magnitude offset a real
    instrument's filter response introduces for a star of a given B-V colour,
    m_std = m_inst + zp + (this). Returns 0 if colour is unknown or the band has
    no term. Reported alongside the SNR; it does not affect the SNR value."""
    if colour_bv is None:
        return 0.0
    return round(COLOUR_TERM.get(filter_band, 0.0) * colour_bv, 4)

def get_surface_brightness(total_magnitude,
                           angular_size_arcmin):
    if (angular_size_arcmin is None or
            angular_size_arcmin <= 0):
        return total_magnitude
    angular_size_arcsec = angular_size_arcmin * 60
    radius_arcsec = angular_size_arcsec / 2
    area_arcsec2  = math.pi * radius_arcsec ** 2
    return round(
        total_magnitude + 2.5 * math.log10(area_arcsec2),
        2
    )

def is_extended_object(object_name):
    if not object_name:
        return False
    extended_keywords = [
        "galaxy", "nebula", "cluster", "cloud",
        "M31", "M33", "M42", "M45", "M8", "M17",
        "M20", "M16", "M27", "M57", "M97",
        "NGC", "LMC", "SMC", "Andromeda",
        "Whirlpool", "Orion", "Lagoon", "Eagle",
        "Omega", "Trifid", "Ring", "Dumbbell",
        "Helix", "Tarantula", "Rosette", "Crab",
        "Sunflower", "Sombrero", "Pinwheel",
        "Triangulum", "Cigar", "Bode"
    ]
    name_lower = object_name.lower()
    return any(
        kw.lower() in name_lower
        for kw in extended_keywords
    )

# ── Photometric zero-points (Vega system) ─────────────────────────
# Flux density of a 0-magnitude Vega-system star, per band, in Jansky.
# GOWC's object magnitudes are Johnson-Cousins/Vega (e.g. Sirius V=-1.46),
# NOT AB, so a single flat 3631 Jy (the AB zero-point) is only right at ~V and
# over-/under-estimates flux badly in the red and IR. These are the standard
# Bessell (1998) Vega zero-points. Falling back to 3631 keeps AB behaviour.
# Reference: Bessell, Castelli & Plez (1998), A&A 333, 231, Table A2.
VEGA_ZERO_POINT_JY = {
    "U": 1810.0,
    "B": 4260.0,
    "V": 3640.0,
    "R": 3080.0,
    "I": 2550.0,
    "J": 1600.0,
    "H": 1080.0,
    "K": 670.0,
}

def mag_to_flux(magnitude, zero_point=3631, band=None):
    """Vega/AB magnitude to flux density (Jy). If a photometric band is given,
    use that band's Vega zero-point; otherwise use the supplied zero_point
    (default 3631 Jy = AB)."""
    if band is not None:
        zero_point = VEGA_ZERO_POINT_JY.get(band, zero_point)
    return zero_point * 10 ** (-magnitude / 2.5)

def flux_to_photons(flux_jy, aperture_m,
                    bandwidth_nm=100,
                    wavelength_nm=550,
                    throughput=0.75,
                    qe=0.85,
                    obstruction=0.0):
    """Photon rate (e-/s) from flux density. `obstruction` is the linear
    diameter ratio of the central obstruction (secondary mirror); the blocked
    area (obstruction^2 of the aperture) is removed from the collecting area."""
    h = 6.626e-34
    c = 3e8
    wavelength_m = wavelength_nm * 1e-9
    energy_per_photon = (h * c) / wavelength_m
    # Effective collecting area with the central obstruction removed.
    obstruction = min(max(obstruction or 0.0, 0.0), 0.9)
    area_m2 = math.pi * (aperture_m / 2) ** 2 * (1.0 - obstruction ** 2)
    bandwidth_hz = (
        (c / wavelength_m**2) *
        (bandwidth_nm * 1e-9)
    )
    flux_wm2 = flux_jy * 1e-26 * bandwidth_hz
    photon_rate = (
        flux_wm2 * area_m2 * throughput * qe
    ) / energy_per_photon
    return max(0, photon_rate)

def scintillation_sigma(aperture_m, exposure_time_s, airmass=1.0,
                        site_altitude_m=2000.0, median_correction=1.5):
    """Fractional scintillation noise sigma_Y (dimensionless) via the modern
    Osborn et al. (2015) form of Young's approximation:

        sigma_Y^2 = 10e-6 * C_Y^2 * D^(-4/3) * t^(-1) * X^3 * exp(-2 h/H)

    where D = aperture (m), t = exposure (s), X = airmass = sec(zenith), h =
    site altitude (m), H ~ 8000 m the turbulence scale height, and C_Y ~ 1.5 is
    the empirical median correction (Kornilov et al. 2012; Osborn et al. 2015),
    which corrects Young's classic underestimate. Note X^3 = (cos gamma)^(-3).

    Reference: Osborn, Foehring, Dhillon & Wilson (2015), MNRAS 452, 1707,
    "Atmospheric scintillation in astronomical photometry", Eq. 2.

    Returns sigma_Y (the fractional flux standard deviation); multiply by the
    source counts to get the scintillation noise contribution."""
    if not (aperture_m and aperture_m > 0 and exposure_time_s and exposure_time_s > 0):
        return 0.0
    H = 8000.0
    X = max(1.0, airmass)
    h = max(0.0, site_altitude_m or 0.0)
    sigma2 = (10e-6 * (median_correction ** 2)
              * aperture_m ** (-4.0 / 3.0)
              * (1.0 / exposure_time_s)
              * (X ** 3)
              * math.exp(-2.0 * h / H))
    return math.sqrt(max(0.0, sigma2))


def snr_quality(snr):
    if snr >= 100:  return "Exceptional — publication quality"
    elif snr >= 50: return "Excellent — high precision work"
    elif snr >= 20: return "Good — reliable detection"
    elif snr >= 10: return "Moderate — clear detection"
    elif snr >= 5:  return "Marginal — weak detection"
    elif snr >= 3:  return "Poor — barely detectable"
    else:           return "Undetectable"

# ── Main SNR calculation ──────────────────────────────────────────
def calculate_snr(
    object_magnitude,
    exposure_time_s,
    telescope_specs,
    sky_brightness_mag,
    seeing_arcsec,
    object_name=None,
    object_altitude_deg=None,
    object_angular_size_arcsec=None,
    pwv_mm=None,
    telescope_type="optical",
    site_altitude_m=2000.0,
    filter_band="V",
    wavelength_nm=550.0,
    bandwidth_nm=100.0,
    extinction_coeff=None,
    colour_bv=None
):
    aperture     = telescope_specs["aperture_m"]
    pixel_scale  = telescope_specs["pixel_scale"]
    read_noise   = telescope_specs["read_noise"]
    dark_current = telescope_specs["dark_current"]
    qe           = telescope_specs["quantum_efficiency"]
    throughput   = telescope_specs["throughput"]
    # Central obstruction (secondary mirror), as a linear diameter ratio.
    # Optional in the specs dict; 0 = unobstructed (refractor / no data).
    obstruction  = telescope_specs.get("obstruction", 0.0)
    # Detector full-well / saturation limit (electrons per pixel). Optional.
    full_well_e  = telescope_specs.get("full_well_e")
    # Published zero-point (e-/s for a mag-0 star, above atmosphere). When a real
    # instrument+filter supplies this, it already folds in area, optics
    # throughput, filter response and detector QE, so we use it DIRECTLY and skip
    # the generic throughput*QE photon-counting path (which would double-count).
    zp_per_sec   = telescope_specs.get("zp_per_sec")
    # Empirical/theoretical efficiency: the measured end-to-end efficiency as a
    # fraction of the idealised optical calculation (dust, real coatings, aging).
    # SIGNAL exposes this explicitly; e.g. INT/WFC ~0.70, ACAM 1.00. Defaults to
    # 1.0 (pure theoretical). Applied to both source and sky photon rates.
    empirical_eff = telescope_specs.get("empirical_efficiency", 1.0) or 1.0

    # If a resolved instrument config was passed (from instruments.py), let its
    # own filter/site fields drive the calculation. Explicit non-default caller
    # arguments still win; these fill in from the instrument when the caller
    # left the defaults in place.
    if telescope_specs.get("band") and filter_band == "V":
        filter_band = telescope_specs["band"]
    if telescope_specs.get("wavelength_nm") and wavelength_nm == 550.0:
        wavelength_nm = telescope_specs["wavelength_nm"]
    if telescope_specs.get("bandwidth_nm") and bandwidth_nm == 100.0:
        bandwidth_nm = telescope_specs["bandwidth_nm"]
    if telescope_specs.get("altitude_m") and site_altitude_m == 2000.0:
        site_altitude_m = telescope_specs["altitude_m"]

    # PWV transmission for infrared
    if telescope_type == "infrared" and pwv_mm:
        pwv_transmission = math.exp(-pwv_mm / 10)
        throughput       = throughput * pwv_transmission
    else:
        pwv_transmission = 1.0

    # Atmospheric extinction. An explicit extinction_coeff (mag/airmass)
    # overrides the site-altitude-derived value — used by the SNR page's manual
    # mode to match an ETC exactly.
    if object_altitude_deg is not None:
        ext_transmission = atmospheric_extinction(
            object_altitude_deg,
            extinction_coeff=extinction_coeff,
            site_altitude_m=site_altitude_m,
            filter_band=filter_band,
            colour_bv=colour_bv)
        effective_throughput = throughput * ext_transmission
        airmass = (
            1 / math.sin(
                math.radians(max(1, object_altitude_deg)))
            if object_altitude_deg > 0 else 40
        )
    else:
        effective_throughput = throughput
        airmass              = 1.5
        ext_transmission     = 0.85

    # ── Extended vs point source ──────────────────────────────────
    # For an extended object we do NOT collect its whole integrated magnitude in
    # one seeing disk — we measure the flux WITHIN the photometry aperture. So:
    #   surface brightness  SB = m_total + 2.5*log10(object_area_arcsec^2)
    #   aperture magnitude  m_ap = SB - 2.5*log10(aperture_area_arcsec^2)
    # i.e. we scale the total light down by (aperture_area / object_area). The
    # aperture is a seeing disk (radius ~ seeing FWHM). This replaces the old
    # code, which plugged the whole-object surface brightness straight in as a
    # total magnitude and drove large objects to SNR 0.
    angular_size_arcmin = None
    if object_name:
        angular_size_arcmin = OBJECT_ANGULAR_SIZES.get(object_name, 0)
        if (not angular_size_arcmin) and is_extended_object(object_name):
            angular_size_arcmin = 10.0

    # Photometry aperture: a seeing disk (or the object, whichever is smaller).
    _seeing_fwhm = seeing_arcsec or 1.5
    _ap_radius_arcsec = _seeing_fwhm  # ~1 FWHM radius aperture
    aperture_area_arcsec2 = math.pi * _ap_radius_arcsec ** 2

    if (angular_size_arcmin and
            angular_size_arcmin > 0 and
            is_extended_object(object_name)):
        is_extended = True
        object_radius_arcsec = (angular_size_arcmin * 60.0) / 2.0
        object_area_arcsec2 = math.pi * object_radius_arcsec ** 2
        # Fraction of the object's light falling in the photometry aperture.
        frac = min(1.0, aperture_area_arcsec2 / object_area_arcsec2)
        # m_ap = m_total - 2.5*log10(fraction of light in the aperture).
        effective_magnitude = object_magnitude - 2.5 * math.log10(frac)
        # Surface brightness (mag/arcsec^2) kept for reporting.
        surface_brightness_mag = get_surface_brightness(
            object_magnitude, angular_size_arcmin)
    else:
        effective_magnitude = object_magnitude
        is_extended         = False
        surface_brightness_mag = None

    if zp_per_sec:
        # ── Published-ZP path (real instrument) ───────────────────
        # Count rate = ZP(e-/s for mag 0) x 10^(-mag/2.5), then attenuate by
        # atmospheric extinction (the ZP is above-atmosphere/zenith) and, for
        # IR, PWV. Throughput/QE are already baked into the ZP.
        atmos = ext_transmission * pwv_transmission
        source_rate    = (zp_per_sec * 10 ** (-effective_magnitude / 2.5)
                          * atmos * empirical_eff)
        source_counts  = source_rate * exposure_time_s
        # Sky brightness is per arcsec^2; scale by pixel area to get per-pixel.
        sky_rate_pixel = (zp_per_sec * 10 ** (-sky_brightness_mag / 2.5)
                          * atmos * (pixel_scale ** 2) * empirical_eff)
    else:
        # ── Computed path (Vega zero-point x throughput x QE) ─────
        # Source signal — photon collection depends on the chosen filter's
        # central wavelength and bandwidth. Use the band's Vega zero-point so
        # red/IR fluxes are correct (not the flat AB value).
        source_flux   = mag_to_flux(effective_magnitude, band=filter_band)
        source_rate   = flux_to_photons(
            source_flux, aperture,
            bandwidth_nm=bandwidth_nm, wavelength_nm=wavelength_nm,
            throughput=effective_throughput, qe=qe, obstruction=obstruction
        ) * empirical_eff
        source_counts = source_rate * exposure_time_s

        # Sky background per pixel (same band zero-point as the source)
        sky_flux       = mag_to_flux(sky_brightness_mag, band=filter_band)
        sky_rate_pixel = flux_to_photons(
            sky_flux, aperture,
            bandwidth_nm=bandwidth_nm, wavelength_nm=wavelength_nm,
            throughput=effective_throughput, qe=qe, obstruction=obstruction
        ) * (pixel_scale ** 2) * empirical_eff

    # Number of pixels in the photometry aperture. The aperture has RADIUS =
    # 1 FWHM (a ~2xFWHM diameter), the standard point-source aperture that
    # captures the PSF wings — matching the ING SIGNAL ETC (validated to 0.1%)
    # and the signal aperture used for extended objects above. (The earlier
    # 1/2-FWHM radius aperture summed too few sky/read-noise pixels and read
    # SNR ~20% high.)
    effective_seeing = max(
        seeing_arcsec or 1.5,
        object_angular_size_arcsec or 0
    )
    n_pixels = math.pi * (
        effective_seeing / pixel_scale
    ) ** 2
    n_pixels = max(1, round(n_pixels))

    sky_counts  = sky_rate_pixel * exposure_time_s * n_pixels
    dark_counts = dark_current * exposure_time_s * n_pixels
    read_counts = (read_noise ** 2) * n_pixels

    # Scintillation — Osborn et al. (2015) median-corrected Young's form, which
    # (unlike the old D^-2/3 t^-1/2 approximation) has the correct D^-4/3 t^-1
    # dependence plus airmass (X^3) and site-altitude (exp(-2h/H)) terms.
    sigma_scint = scintillation_sigma(
        aperture, exposure_time_s, airmass=airmass,
        site_altitude_m=site_altitude_m)
    scint_noise = sigma_scint * source_counts

    # Total noise and SNR
    total_noise = math.sqrt(
        source_counts +
        sky_counts +
        dark_counts +
        read_counts +
        scint_noise ** 2
    )
    snr = source_counts / total_noise if total_noise > 0 else 0

    # ── Saturation check ──────────────────────────────────────────
    # Mean signal in a PSF-footprint pixel (source spread over n_pixels, plus
    # sky and dark). A point source actually peaks higher than the mean, so we
    # apply a ~3x peak-to-mean factor as a conservative early warning. If the
    # detector's full well is exceeded, photometry is non-linear/unusable and
    # the headline SNR is not trustworthy.
    peak_pixel_e = None
    is_saturated = False
    if full_well_e:
        mean_pixel_e = (source_counts + sky_counts + dark_counts) / n_pixels
        peak_pixel_e = mean_pixel_e * (1.0 if is_extended else 3.0)
        is_saturated = peak_pixel_e > full_well_e

    # ── Honest uncertainty band ───────────────────────────────────
    # The single SNR number hides real modelling uncertainty. The dominant
    # terms an observer cannot pin down from a forecast are: delivered seeing
    # (GOWC's is ~1.5x high and uncalibrated -> sky/pixel count uncertain),
    # scintillation amplitude (C_Y scatter, ~+/-30%), and transparency (thin
    # cirrus). We propagate a seeing swing of x0.7..x1.5 through the sky term to
    # bracket the SNR, giving an optimistic/pessimistic pair rather than false
    # precision. This is a planning band, not a formal error bar.
    def _snr_with_seeing(seeing_factor):
        npx = max(1, round(math.pi * (
            (effective_seeing * seeing_factor) / pixel_scale) ** 2))
        sky_c = sky_rate_pixel * exposure_time_s * npx
        dark_c = dark_current * exposure_time_s * npx
        read_c = (read_noise ** 2) * npx
        noise = math.sqrt(source_counts + sky_c + dark_c + read_c
                          + scint_noise ** 2)
        return source_counts / noise if noise > 0 else 0
    # Better seeing (x0.7) -> higher SNR; worse (x1.5) -> lower.
    snr_optimistic = round(_snr_with_seeing(0.7), 1)
    snr_pessimistic = round(_snr_with_seeing(1.5), 1)

    # Limiting magnitude
    lim_mag  = object_magnitude
    step     = 0.5
    for _ in range(50):
        if zp_per_sec:
            test_rate = (zp_per_sec * 10 ** (-(lim_mag + step) / 2.5)
                         * ext_transmission * pwv_transmission * empirical_eff)
        else:
            test_flux = mag_to_flux(lim_mag + step, band=filter_band)
            test_rate = flux_to_photons(
                test_flux, aperture,
                bandwidth_nm=bandwidth_nm, wavelength_nm=wavelength_nm,
                throughput=effective_throughput, qe=qe, obstruction=obstruction
            ) * empirical_eff
        test_counts = test_rate * exposure_time_s
        test_noise  = math.sqrt(
            test_counts + sky_counts +
            dark_counts + read_counts
        )
        test_snr = (
            test_counts / test_noise
            if test_noise > 0 else 0
        )
        if test_snr >= 5:
            lim_mag += step
        else:
            step /= 2
        if step < 0.01:
            break

    # Time to reach SNR targets
    def time_for_snr(target_snr):
        a = source_rate ** 2 - (
            target_snr ** 2 * source_rate)
        b = -(target_snr ** 2) * (
            sky_rate_pixel * n_pixels +
            dark_current * n_pixels
        )
        c = -(target_snr ** 2) * read_counts
        if a <= 0:
            return None
        discriminant = b**2 - 4*a*c
        if discriminant < 0:
            return None
        t = (-b + math.sqrt(discriminant)) / (2 * a)
        return round(max(1, t), 1)

    def format_time(t):
        if t is None:
            return "Not achievable"
        if t < 60:
            return f"{t:.0f} seconds"
        elif t < 3600:
            return f"{t/60:.1f} minutes"
        else:
            return f"{t/3600:.1f} hours"

    return {
        "snr":                round(snr, 1),
        "snr_quality":        snr_quality(snr),
        # Photometric uncertainty on the magnitude: sigma_m = 1.0857 / SNR
        # (from sigma_m = 2.5/ln(10) * sigma_f/f, with sigma_f/f = 1/SNR).
        "sigma_mag":          (round(1.0857 / snr, 4) if snr > 0 else None),
        # Instrumental->standard colour term for this band and target colour
        # (0 if colour unknown). A reporting quantity; does not affect the SNR.
        "colour_term":        colour_correction(filter_band, colour_bv),
        # Honest planning band (seeing x0.7..x1.5); pessimistic < snr < optimistic.
        "snr_optimistic":     snr_optimistic,
        "snr_pessimistic":    snr_pessimistic,
        # Saturation warning (None if the detector has no full_well_e in specs).
        "is_saturated":       is_saturated,
        "peak_pixel_e":       round(peak_pixel_e, 0) if peak_pixel_e else None,
        "full_well_e":        full_well_e,
        "source_counts":      round(source_counts, 1),
        "sky_counts":         round(sky_counts, 1),
        "dark_counts":        round(dark_counts, 1),
        "read_counts":        round(read_counts, 1),
        "scint_noise":        round(scint_noise, 1),
        "total_noise":        round(total_noise, 1),
        "n_pixels":           n_pixels,
        "limiting_magnitude": round(lim_mag, 1),
        "pwv_transmission":   round(pwv_transmission, 3),
        "ext_transmission":   ext_transmission,
        "airmass":            round(airmass, 2),
        "is_extended":        is_extended,
        "effective_magnitude": round(
            effective_magnitude, 2),
        "surface_brightness_mag": (round(surface_brightness_mag, 2)
                                   if surface_brightness_mag is not None
                                   else None),
        "angular_size_arcmin": angular_size_arcmin,
        "time_for_snr5":      format_time(time_for_snr(5)),
        "time_for_snr10":     format_time(time_for_snr(10)),
        "time_for_snr50":     format_time(time_for_snr(50)),
        "time_for_snr100":    format_time(time_for_snr(100)),
        "noise_budget": {
            "shot_noise":    round(
                math.sqrt(source_counts), 1),
            "sky_noise":     round(
                math.sqrt(sky_counts), 1),
            "dark_noise":    round(
                math.sqrt(dark_counts), 1),
            "read_noise":    round(
                math.sqrt(read_counts), 1),
            "scintillation": round(scint_noise, 1)
        }
    }

def get_snr_for_all_observatories(
    object_name,
    object_magnitude,
    exposure_time_s,
    observatories_df,
    moon_phase_pct,
    moon_altitude_deg,
    seeing_data=None,
    pwv_data=None
):
    import pandas as pd
    results = []
    sky_brightness = get_sky_brightness(
        moon_phase_pct, moon_altitude_deg)

    for _, row in observatories_df.iterrows():
        obs_name = row["observatory"]
        specs    = get_telescope_specs(
            obs_name, row.get("altitude_m", 0))

        seeing = 1.5
        if seeing_data is not None:
            obs_seeing = seeing_data[
                seeing_data["observatory"] == obs_name]
            if not obs_seeing.empty:
                seeing = (
                    obs_seeing.iloc[0].get(
                        "seeing_arcsec", 1.5)
                    or 1.5
                )

        pwv = None
        if pwv_data is not None:
            obs_pwv = pwv_data[
                pwv_data["observatory"] == obs_name]
            if not obs_pwv.empty:
                pwv = obs_pwv.iloc[0].get("pwv_mm")

        try:
            result = calculate_snr(
                object_magnitude   = object_magnitude,
                exposure_time_s    = exposure_time_s,
                telescope_specs    = specs,
                sky_brightness_mag = sky_brightness,
                seeing_arcsec      = seeing,
                object_name        = object_name,
                pwv_mm             = pwv,
                site_altitude_m    = row.get("altitude_m", 2000) or 2000
            )
            results.append({
                "observatory":   obs_name,
                "country":       row["country"],
                "telescope":     specs.get(
                    "name",
                    f"{specs['aperture_m']}m telescope"
                ),
                "aperture_m":    specs["aperture_m"],
                "snr":           result["snr"],
                "snr_quality":   result["snr_quality"],
                "limiting_mag":  result["limiting_magnitude"],
                "time_snr5":     result["time_for_snr5"],
                "time_snr10":    result["time_for_snr10"],
                "time_snr50":    result["time_for_snr50"],
                "time_snr100":   result["time_for_snr100"],
                "sky_brightness": sky_brightness,
                "seeing":        seeing,
                "noise_budget":  result["noise_budget"]
            })
        except Exception:
            continue

    return pd.DataFrame(results).sort_values(
        "snr", ascending=False)


if __name__ == "__main__":
    print("\n Testing SNR Calculator\n")
    specs  = TELESCOPE_SPECS["Paranal Observatory"]
    result = calculate_snr(
        object_magnitude   = 8.4,
        exposure_time_s    = 300,
        telescope_specs    = specs,
        sky_brightness_mag = 21.5,
        seeing_arcsec      = 0.65,
        object_name        = "M1 — Crab Nebula",
        pwv_mm             = 2.5
    )
    print(f"  Object       : M1 Crab Nebula")
    print(f"  Telescope    : VLT 8.2m at Paranal")
    print(f"  Exposure     : 5 minutes")
    print(f"  SNR          : {result['snr']}")
    print(f"  Quality      : {result['snr_quality']}")
    print(f"  Limit mag    : {result['limiting_magnitude']}")
    print(f"  Extended obj : {result['is_extended']}")
    print(f"  Eff mag      : {result['effective_magnitude']}")
    print(f"\n  Time for SNR 10  : {result['time_for_snr10']}")
    print(f"  Time for SNR 50  : {result['time_for_snr50']}")