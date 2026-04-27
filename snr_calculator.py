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

# ── Helper functions ──────────────────────────────────────────────
def get_sky_brightness(moon_phase_pct, moon_altitude_deg):
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

def atmospheric_extinction(altitude_deg,
                           extinction_coeff=0.12):
    if altitude_deg is None or altitude_deg <= 0:
        return 0.5
    if altitude_deg >= 90:
        airmass = 1.0
    elif altitude_deg < 1:
        airmass = 40.0
    else:
        airmass = 1 / math.sin(math.radians(altitude_deg))
    extinction_mag = extinction_coeff * airmass
    transmission   = 10 ** (-extinction_mag / 2.5)
    return round(min(1.0, max(0.0, transmission)), 4)

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

def mag_to_flux(magnitude, zero_point=3631):
    return zero_point * 10 ** (-magnitude / 2.5)

def flux_to_photons(flux_jy, aperture_m,
                    bandwidth_nm=100,
                    wavelength_nm=550,
                    throughput=0.75,
                    qe=0.85):
    h = 6.626e-34
    c = 3e8
    wavelength_m = wavelength_nm * 1e-9
    energy_per_photon = (h * c) / wavelength_m
    area_m2 = math.pi * (aperture_m / 2) ** 2
    bandwidth_hz = (
        (c / wavelength_m**2) *
        (bandwidth_nm * 1e-9)
    )
    flux_wm2 = flux_jy * 1e-26 * bandwidth_hz
    photon_rate = (
        flux_wm2 * area_m2 * throughput * qe
    ) / energy_per_photon
    return max(0, photon_rate)

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
    telescope_type="optical"
):
    aperture     = telescope_specs["aperture_m"]
    pixel_scale  = telescope_specs["pixel_scale"]
    read_noise   = telescope_specs["read_noise"]
    dark_current = telescope_specs["dark_current"]
    qe           = telescope_specs["quantum_efficiency"]
    throughput   = telescope_specs["throughput"]

    # PWV transmission for infrared
    if telescope_type == "infrared" and pwv_mm:
        pwv_transmission = math.exp(-pwv_mm / 10)
        throughput       = throughput * pwv_transmission
    else:
        pwv_transmission = 1.0

    # Atmospheric extinction
    if object_altitude_deg is not None:
        ext_transmission = atmospheric_extinction(
            object_altitude_deg)
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

    # Surface brightness for extended objects
    angular_size_arcmin = None
    if object_name:
        angular_size_arcmin = OBJECT_ANGULAR_SIZES.get(
            object_name, 0)

    if (angular_size_arcmin and
            angular_size_arcmin > 0 and
            is_extended_object(object_name)):
        effective_magnitude = get_surface_brightness(
            object_magnitude, angular_size_arcmin)
        is_extended = True
    else:
        effective_magnitude = object_magnitude
        is_extended         = False

    # Source signal
    source_flux   = mag_to_flux(effective_magnitude)
    source_rate   = flux_to_photons(
        source_flux, aperture,
        throughput=effective_throughput, qe=qe
    )
    source_counts = source_rate * exposure_time_s

    # Sky background per pixel
    sky_flux       = mag_to_flux(sky_brightness_mag)
    sky_rate_pixel = flux_to_photons(
        sky_flux, aperture,
        throughput=effective_throughput, qe=qe
    ) * (pixel_scale ** 2)

    # Number of pixels
    effective_seeing = max(
        seeing_arcsec or 1.5,
        object_angular_size_arcsec or 0
    )
    n_pixels = math.pi * (
        effective_seeing / (2 * pixel_scale)
    ) ** 2
    n_pixels = max(1, round(n_pixels))

    sky_counts  = sky_rate_pixel * exposure_time_s * n_pixels
    dark_counts = dark_current * exposure_time_s * n_pixels
    read_counts = (read_noise ** 2) * n_pixels

    # Scintillation
    if seeing_arcsec and aperture and exposure_time_s > 0:
        scint_coeff = (
            0.09 * (aperture ** (-2/3)) *
            (1.0 / math.sqrt(exposure_time_s))
        )
        scint_noise = scint_coeff * source_counts
    else:
        scint_noise = 0

    # Total noise and SNR
    total_noise = math.sqrt(
        source_counts +
        sky_counts +
        dark_counts +
        read_counts +
        scint_noise ** 2
    )
    snr = source_counts / total_noise if total_noise > 0 else 0

    # Limiting magnitude
    lim_mag  = object_magnitude
    step     = 0.5
    for _ in range(50):
        test_flux   = mag_to_flux(lim_mag + step)
        test_rate   = flux_to_photons(
            test_flux, aperture,
            throughput=effective_throughput, qe=qe
        )
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
                pwv_mm             = pwv
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