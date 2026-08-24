"""
Validate GOWC's SNR calculator against the ING SIGNAL Exposure Time Calculator.

SIGNAL (https://astro.ing.iac.es/signal/) is the official ETC for the Isaac
Newton Group telescopes on La Palma. This script reproduces two real SIGNAL runs
— WHT/ACAM and INT/WFC, both V band — and checks GOWC agrees.

Each benchmark records the EXACT SIGNAL inputs and its reported outputs (object
counts, sky counts, SNR), and feeds GOWC either SIGNAL's own instrument
constants (ACAM) or the catalogue entry that was tuned to SIGNAL (WFC). A
planning-grade tool is expected to agree within ~10 %; we PASS at <=10 % on SNR.

Run:  python tests/validate_snr_etc.py

Result (2026 validation):
    WHT/ACAM  GOWC 151.9  vs SIGNAL 150.56   ratio 1.009   PASS
    INT/WFC   GOWC  92.1  vs SIGNAL  89.20   ratio 1.033   PASS
"""
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snr_calculator import calculate_snr           # noqa: E402
from instruments import get_instrument_config       # noqa: E402


def _alt_from_airmass(x):
    """Effective object altitude (deg) for a plane-parallel airmass X."""
    return math.degrees(math.asin(min(1.0, 1.0 / x)))


# ─────────────────────────────────────────────────────────────────
# Benchmark 1 — WHT / ACAM / V
# SIGNAL inputs: point source, m=20 (Vega), 100 s, seeing 1.0", airmass 1.0,
#   extinction 0.12, sky "D" (21.50 mag/arcsec^2).
# SIGNAL reported: object 40839 e-, sky 643.7 e-/pix, SNR 150.56.
# GOWC is fed SIGNAL's own reported constants (area 12.47 m^2 -> aperture,
#   throughput tel*instr = 0.72*0.71, QE 0.85, bandwidth 860 A = 86 nm, RN 3.2),
#   which isolates the CCD-equation bookkeeping from catalogue estimates.
# ─────────────────────────────────────────────────────────────────
def _acam_specs():
    area_m2 = 12.47
    aperture = math.sqrt(area_m2 / math.pi) * 2
    return {
        "aperture_m": aperture, "pixel_scale": 0.25, "read_noise": 3.2,
        "dark_current": 0.0, "quantum_efficiency": 0.85,
        "throughput": 0.72 * 0.71, "obstruction": 0.0,
        "full_well_e": None, "type": "optical",
    }


ACAM = {
    "label":       "WHT / ACAM / V",
    "specs":       _acam_specs(),
    "kwargs": dict(
        object_magnitude=20.0, exposure_time_s=100,
        sky_brightness_mag=21.50, seeing_arcsec=1.0,
        object_altitude_deg=90.0, filter_band="V",
        wavelength_nm=550.0, bandwidth_nm=86.0, extinction_coeff=0.12,
    ),
    "signal_snr":  150.56,
    "signal_obj":  40839.0,
}


# ─────────────────────────────────────────────────────────────────
# Benchmark 2 — INT / WFC / V
# SIGNAL inputs: point source, m=20 (Vega), 100 s, seeing 1.0", airmass 1.0,
#   extinction 0.12, sky "D" (21.50 mag/arcsec^2).
# SIGNAL reported: object 14425 e-, sky 402.9 e-/pix, SNR 89.20.
# The key term SIGNAL applies is an "empirical/theoretical" efficiency of 0.70;
# GOWC's WFC catalogue entry carries empirical_efficiency=0.70, so we validate
# through the catalogue (get_instrument_config) directly.
# ─────────────────────────────────────────────────────────────────
WFC = {
    "label":       "INT / WFC / V",
    "specs":       get_instrument_config(
        "Isaac Newton Telescope (INT)", "WFC (Wide Field Camera)", "V (visual)"),
    "kwargs": dict(
        object_magnitude=20.0, exposure_time_s=100,
        sky_brightness_mag=21.50, seeing_arcsec=1.0,
        object_altitude_deg=90.0, extinction_coeff=0.12,
    ),
    "signal_snr":  89.20,
    "signal_obj":  14425.0,
}


BENCHMARKS = [ACAM, WFC]
TOLERANCE = 0.10   # PASS if |ratio - 1| <= 10 %


def run_benchmark(bench):
    r = calculate_snr(telescope_specs=bench["specs"], **bench["kwargs"])
    snr, obj = r["snr"], r["source_counts"]
    snr_ratio = snr / bench["signal_snr"]
    obj_ratio = obj / bench["signal_obj"]
    passed = abs(snr_ratio - 1.0) <= TOLERANCE
    return snr, obj, snr_ratio, obj_ratio, passed


def main():
    print("\n  GOWC vs ING SIGNAL — SNR validation\n")
    print(f"  {'instrument':16s} {'GOWC':>8} {'SIGNAL':>8} {'SNR ratio':>10} "
          f"{'obj ratio':>10}  {'verdict'}")
    print("  " + "-" * 68)
    all_pass = True
    for b in BENCHMARKS:
        snr, obj, sr, orat, ok = run_benchmark(b)
        all_pass = all_pass and ok
        print(f"  {b['label']:16s} {snr:8.1f} {b['signal_snr']:8.2f} "
              f"{sr:10.3f} {orat:10.3f}  {'PASS' if ok else 'FAIL'}")
    print("  " + "-" * 68)
    print(f"\n  {'ALL PASS' if all_pass else 'SOME FAILED'} "
          f"(tolerance {int(TOLERANCE*100)} % on SNR)\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
