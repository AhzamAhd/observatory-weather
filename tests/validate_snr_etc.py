"""
Validate GOWC's SNR calculator against the ING SIGNAL Exposure Time Calculator.

SIGNAL (https://astro.ing.iac.es/signal/) is the official ETC for the Isaac
Newton Group telescopes on La Palma. This script reproduces two real SIGNAL runs
— WHT/ACAM and INT/WFC, both V band — and checks GOWC agrees.

Each benchmark records the EXACT SIGNAL inputs and its reported outputs (object
counts, sky counts, SNR), and feeds GOWC either SIGNAL's own instrument
GOWC's own catalogue entries (instruments.py), whose constants are SIGNAL's
definitions of each instrument. A planning-grade tool is expected to agree
within ~10 %; we PASS at <=10 % on SNR.

Note: a second SIGNAL run at nominally identical ACAM inputs (the m=20, X=1
anchor of tests/snr_grid_compare.py) returned SNR 152.66 rather than 150.56 --
a 1.4 % run-to-run difference in SIGNAL itself that bounds benchmark precision.

Run:  python tests/validate_snr_etc.py

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
# GOWC's catalogue ACAM entry carries SIGNAL's constants (collecting area
#   12.47 m^2, throughput tel*instr = 0.72*0.71, QE 0.85, 86 nm, RN 3.2, 0.25").
# ─────────────────────────────────────────────────────────────────
ACAM = {
    "label":       "WHT / ACAM / V",
    "specs":       get_instrument_config(
        "William Herschel Telescope (WHT)", "ACAM (imaging)", "V (visual)"),
    "kwargs": dict(
        object_magnitude=20.0, exposure_time_s=100,
        sky_brightness_mag=21.50, seeing_arcsec=1.0,
        object_altitude_deg=90.0, filter_band="V", extinction_coeff=0.12,
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
          f"{'obj ratio':>10}  {'GOWC obj':>9}  {'verdict'}")
    print("  " + "-" * 68)
    all_pass = True
    for b in BENCHMARKS:
        snr, obj, sr, orat, ok = run_benchmark(b)
        all_pass = all_pass and ok
        print(f"  {b['label']:16s} {snr:8.1f} {b['signal_snr']:8.2f} "
              f"{sr:10.3f} {orat:10.3f}  {obj:9.0f}  {'PASS' if ok else 'FAIL'}")
    print("  " + "-" * 68)
    print(f"\n  {'ALL PASS' if all_pass else 'SOME FAILED'} "
          f"(tolerance {int(TOLERANCE*100)} % on SNR)\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
