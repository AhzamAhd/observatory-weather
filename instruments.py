"""
Real instrument specifications for the SNR calculator.

A small, curated, *citable* catalogue of real telescope+instrument+filter
combinations. Each entry carries the constants the CCD equation actually needs,
sourced from instrument papers, observatory ETC pages, and instrument manuals.

Structure:  facility -> instrument -> {shared detector/optics specs, filters}

Two zero-point modes are supported per filter (this is the key physics choice):

  * "published"  — the filter carries `zp_per_sec`: the count rate (e-/s) a
                   magnitude-0 star produces at the top of the atmosphere
                   through this exact instrument+filter. This number already
                   folds in the telescope area, all optics throughput, the
                   filter response, and the detector QE. When present, the SNR
                   engine uses it DIRECTLY and must NOT re-apply throughput*QE
                   (that would double-count). Atmospheric extinction is still
                   applied on top (the ZP is above-atmosphere / zenith).

  * "computed"   — no `zp_per_sec`; the engine falls back to the classic
                   photon-counting path (Vega zero-point flux -> photons over
                   the collecting area x throughput x QE). Used when a clean
                   published ZP isn't available for a mode.

Every instrument lists a `source` string so the numbers are traceable. Where a
value is a reasonable estimate rather than a hard citation, it is marked EST.

Zero-points below are expressed as `zp_per_sec` = e-/s for a mag-0 star. If a
source quotes the more common "magnitude giving 1 e-/s" zero-point ZP1, convert
with zp_per_sec = 10**(ZP1 / 2.5).
"""

# ── Instrument catalogue ──────────────────────────────────────────
# Filter dicts: wavelength_nm, bandwidth_nm, band (for extinction), and either
# zp_per_sec (published mode) or nothing (computed mode).

INSTRUMENTS = {

    # ============================================================
    # La Palma — Isaac Newton Group / robotic
    # ============================================================
    "Isaac Newton Telescope (INT)": {
        "aperture_m":   2.54,
        "altitude_m":   2336,
        "obstruction":  0.30,          # EST, Cassegrain secondary
        "instruments": {
            "WFC (Wide Field Camera)": {
                "detector":     "EEV 4k x 2k CCD mosaic",
                "pixel_scale":  0.333,     # arcsec/pixel
                "read_noise":   3.5,       # e- (chip 4, typical)
                "dark_current": 0.0003,    # e-/pix/s (EST, cooled)
                "gain":         2.9,       # e-/ADU
                "full_well_e":  135000,
                "quantum_efficiency": 0.80,
                "throughput":   0.75,      # EST, telescope+instrument optics
                "source": "ING WFC manual / ETC; Ives et al. detector notes",
                "filters": {
                    # Published ZP1 (mag for 1 e-/s) from ING WFC ETC, converted.
                    "U (ultraviolet)": {"wavelength_nm": 361, "bandwidth_nm": 63,  "band": "U", "zp_per_sec": 10**(24.9/2.5)},
                    "B (blue)":        {"wavelength_nm": 442, "bandwidth_nm": 100, "band": "B", "zp_per_sec": 10**(27.0/2.5)},
                    "V (visual)":      {"wavelength_nm": 540, "bandwidth_nm": 89,  "band": "V", "zp_per_sec": 10**(27.0/2.5)},
                    "R (red)":         {"wavelength_nm": 641, "bandwidth_nm": 148, "band": "R", "zp_per_sec": 10**(27.3/2.5)},
                    "I (near-IR)":     {"wavelength_nm": 799, "bandwidth_nm": 152, "band": "I", "zp_per_sec": 10**(26.5/2.5)},
                },
            },
        },
    },

    "William Herschel Telescope (WHT)": {
        "aperture_m":   4.20,
        "altitude_m":   2344,
        "obstruction":  0.24,          # EST
        "instruments": {
            "ACAM (imaging)": {
                "detector":     "Auxiliary-port camera, deep-depletion CCD",
                "pixel_scale":  0.253,
                "read_noise":   3.3,       # e- (EST, typical)
                "dark_current": 0.0002,    # e-/pix/s (EST)
                "gain":         1.0,
                "full_well_e":  120000,
                "quantum_efficiency": 0.85,
                "throughput":   0.72,      # EST
                "source": "Benn, Dee & Aguerri (2008); ING ACAM ETC",
                "filters": {
                    "B (blue)":   {"wavelength_nm": 440, "bandwidth_nm": 100, "band": "B", "zp_per_sec": 10**(26.8/2.5)},
                    "V (visual)": {"wavelength_nm": 551, "bandwidth_nm": 88,  "band": "V", "zp_per_sec": 10**(27.0/2.5)},
                    "R (red)":    {"wavelength_nm": 640, "bandwidth_nm": 150, "band": "R", "zp_per_sec": 10**(27.2/2.5)},
                    "I (near-IR)":{"wavelength_nm": 810, "bandwidth_nm": 150, "band": "I", "zp_per_sec": 10**(26.4/2.5)},
                },
            },
        },
    },

    "pt5m (Durham/Sheffield 0.5m)": {
        "aperture_m":   0.50,
        "altitude_m":   2360,          # on the WHT building, La Palma
        "obstruction":  0.35,          # EST, small Cassegrain
        "instruments": {
            "Science camera": {
                "detector":     "QSI 532 interline CCD (KAF-3200ME)",
                "pixel_scale":  0.28,
                "read_noise":   8.0,       # e-
                "dark_current": 0.02,      # e-/pix/s (EST, thermoelectric)
                "gain":         1.3,
                "full_well_e":  40000,
                "quantum_efficiency": 0.60,
                "throughput":   0.55,      # EST, small robotic optics
                "source": "Hardy et al. (2015), MNRAS 454, 4316 (pt5m)",
                "filters": {
                    # No clean published ZP for the modes -> computed fallback.
                    "B (blue)":   {"wavelength_nm": 440, "bandwidth_nm": 100, "band": "B"},
                    "V (visual)": {"wavelength_nm": 551, "bandwidth_nm": 88,  "band": "V"},
                    "R (red)":    {"wavelength_nm": 658, "bandwidth_nm": 138, "band": "R"},
                    "I (near-IR)":{"wavelength_nm": 806, "bandwidth_nm": 149, "band": "I"},
                },
            },
        },
    },

    # ============================================================
    # Major facilities
    # ============================================================
    "Very Large Telescope (VLT UT1)": {
        "aperture_m":   8.20,
        "altitude_m":   2635,
        "obstruction":  0.14,
        "instruments": {
            "FORS2 (imaging)": {
                "detector":     "MIT/LL 2x 2k x 4k CCD mosaic",
                "pixel_scale":  0.25,      # standard-resolution collimator
                "read_noise":   2.9,       # e- (100kHz, high gain)
                "dark_current": 0.0008,    # e-/pix/s (EST)
                "gain":         0.7,
                "full_well_e":  200000,
                "quantum_efficiency": 0.90,
                "throughput":   0.70,      # EST
                "source": "Appenzeller et al. (1998); ESO FORS2 ETC",
                "filters": {
                    "U (ultraviolet)": {"wavelength_nm": 365, "bandwidth_nm": 66,  "band": "U", "zp_per_sec": 10**(27.5/2.5)},
                    "B (blue)":        {"wavelength_nm": 429, "bandwidth_nm": 88,  "band": "B", "zp_per_sec": 10**(27.9/2.5)},
                    "V (visual)":      {"wavelength_nm": 554, "bandwidth_nm": 112, "band": "V", "zp_per_sec": 10**(28.0/2.5)},
                    "R (red)":         {"wavelength_nm": 655, "bandwidth_nm": 165, "band": "R", "zp_per_sec": 10**(28.2/2.5)},
                    "I (near-IR)":     {"wavelength_nm": 768, "bandwidth_nm": 138, "band": "I", "zp_per_sec": 10**(27.7/2.5)},
                },
            },
        },
    },

    "Keck I (10m)": {
        "aperture_m":   10.0,
        "altitude_m":   4145,
        "obstruction":  0.14,          # EST (segmented, small effective blockage)
        "instruments": {
            "LRIS (imaging)": {
                "detector":     "LRIS red (LBNL) + blue (Marconi) CCDs",
                "pixel_scale":  0.135,
                "read_noise":   4.0,       # e- (EST)
                "dark_current": 0.001,     # e-/pix/s (EST)
                "gain":         1.6,
                "full_well_e":  100000,
                "quantum_efficiency": 0.88,
                "throughput":   0.55,      # EST (spectrograph imaging mode)
                "source": "Oke et al. (1995); Keck LRIS ETC",
                "filters": {
                    "B (blue)":   {"wavelength_nm": 437, "bandwidth_nm": 90,  "band": "B", "zp_per_sec": 10**(28.5/2.5)},
                    "V (visual)": {"wavelength_nm": 551, "bandwidth_nm": 88,  "band": "V", "zp_per_sec": 10**(28.7/2.5)},
                    "R (red)":    {"wavelength_nm": 658, "bandwidth_nm": 138, "band": "R", "zp_per_sec": 10**(28.9/2.5)},
                    "I (near-IR)":{"wavelength_nm": 806, "bandwidth_nm": 149, "band": "I", "zp_per_sec": 10**(28.4/2.5)},
                },
            },
        },
    },

    "Gemini North (8.1m)": {
        "aperture_m":   8.10,
        "altitude_m":   4213,
        "obstruction":  0.14,          # EST
        "instruments": {
            "GMOS-N (imaging)": {
                "detector":     "Hamamatsu 3x CCD mosaic",
                "pixel_scale":  0.0807,
                "read_noise":   4.1,       # e- (slow read)
                "dark_current": 0.0006,    # e-/pix/s (EST)
                "gain":         1.9,
                "full_well_e":  130000,
                "quantum_efficiency": 0.88,
                "throughput":   0.60,      # EST
                "source": "Hook et al. (2004); Gemini GMOS ITC",
                "filters": {
                    # SDSS-like filters mapped to nearest Johnson band for extinction.
                    "g (green)":  {"wavelength_nm": 475, "bandwidth_nm": 154, "band": "B", "zp_per_sec": 10**(28.3/2.5)},
                    "r (red)":    {"wavelength_nm": 630, "bandwidth_nm": 136, "band": "R", "zp_per_sec": 10**(28.3/2.5)},
                    "i (near-IR)":{"wavelength_nm": 780, "bandwidth_nm": 129, "band": "I", "zp_per_sec": 10**(28.1/2.5)},
                },
            },
        },
    },
}


# ── Accessors ─────────────────────────────────────────────────────
def list_facilities():
    """All facility names, for the first dropdown."""
    return list(INSTRUMENTS.keys())


def list_instruments(facility):
    """Instrument names available at a facility, for the second dropdown."""
    fac = INSTRUMENTS.get(facility)
    return list(fac["instruments"].keys()) if fac else []


def list_filters(facility, instrument):
    """Filter names for a facility+instrument, for the third dropdown."""
    fac = INSTRUMENTS.get(facility)
    if not fac:
        return []
    inst = fac["instruments"].get(instrument)
    return list(inst["filters"].keys()) if inst else []


def get_instrument_config(facility, instrument, filter_name):
    """Resolve a facility+instrument+filter selection into a flat config dict
    the SNR engine consumes. Returns None if the selection is invalid.

    The returned dict is a superset of the old telescope_specs dict (so it drops
    straight into calculate_snr), plus filter fields and, when available, a
    published `zp_per_sec` that puts the engine on the direct-ZP path.
    """
    fac = INSTRUMENTS.get(facility)
    if not fac:
        return None
    inst = fac["instruments"].get(instrument)
    if not inst:
        return None
    filt = inst["filters"].get(filter_name)
    if not filt:
        return None

    cfg = {
        # telescope_specs-compatible fields
        "name":               f"{facility} · {instrument}",
        "aperture_m":         fac["aperture_m"],
        "altitude_m":         fac.get("altitude_m", 0),
        "obstruction":        fac.get("obstruction", 0.0),
        "pixel_scale":        inst["pixel_scale"],
        "read_noise":         inst["read_noise"],
        "dark_current":       inst["dark_current"],
        "quantum_efficiency": inst["quantum_efficiency"],
        "throughput":         inst["throughput"],
        "full_well_e":        inst.get("full_well_e"),
        "gain":               inst.get("gain"),
        "type":               "optical",
        # filter fields
        "filter_name":        filter_name,
        "band":               filt["band"],
        "wavelength_nm":      filt["wavelength_nm"],
        "bandwidth_nm":       filt["bandwidth_nm"],
        # zero-point mode: published (direct) if present, else computed fallback
        "zp_per_sec":         filt.get("zp_per_sec"),
        "zp_mode":            "published" if filt.get("zp_per_sec") else "computed",
        "source":             inst.get("source", ""),
    }
    return cfg


if __name__ == "__main__":
    print("\n  Instrument catalogue\n")
    for fac in list_facilities():
        for inst in list_instruments(fac):
            filts = list_filters(fac, inst)
            print(f"  {fac}")
            print(f"    {inst}: {', '.join(filts)}")
    print("\n  Sample resolved config (WHT/ACAM/V):\n")
    cfg = get_instrument_config(
        "William Herschel Telescope (WHT)", "ACAM (imaging)", "V (visual)")
    for k, v in cfg.items():
        print(f"    {k:20s} {v}")
