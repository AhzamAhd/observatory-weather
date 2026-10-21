"""
Validate GOWC's airmass against the Kasten & Young (1989) approximation formula.

Kasten & Young (1989, Applied Optics 28, 4735) is the standard reference for
optical airmass. Their approximation formula,

    X = 1 / [ sin(h) + 0.50572 (h + 6.07995)^-1.6364 ],   h = altitude in deg,

reproduces their tabulated values closely and, unlike a hand-copied table, can
be recomputed by anyone. GOWC uses the Pickering (2002) interpolative formula;
this script prints both and the percentage difference.

HOW TO RUN IT YOURSELF:
    python tests/validate_airmass.py

Result (PASS if within 1% at and above 5 deg): largest deviation at and above
5 deg 0.27% (at 5 deg); the two forms diverge to ~1.6% at 0.1 deg.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airmass_calculator import altitude_to_airmass   # noqa: E402

ALTITUDES = [90, 80, 70, 60, 50, 40, 30, 20, 15, 10, 5, 2, 1, 0.1]
TOLERANCE_PCT = 1.0   # PASS if within 1% at and above 5 deg
MIN_TESTED_ALT = 5.0


def kasten_young(alt_deg):
    """Kasten & Young (1989) approximation formula."""
    return 1.0 / (math.sin(math.radians(alt_deg))
                  + 0.50572 * (alt_deg + 6.07995) ** -1.6364)


def main():
    print("\n  GOWC (Pickering 2002) airmass vs Kasten & Young (1989) formula\n")
    print(f"  {'alt (deg)':>9} {'GOWC':>9} {'K-Y':>9} {'diff %':>8}  verdict")
    print("  " + "-" * 50)
    worst, worst_alt, all_pass = 0.0, None, True
    for alt in ALTITUDES:
        ky = kasten_young(alt)
        gowc = altitude_to_airmass(alt)
        diff = 100.0 * (gowc - ky) / ky
        tested = alt >= MIN_TESTED_ALT
        ok = abs(diff) <= TOLERANCE_PCT
        if tested:
            all_pass = all_pass and ok
            if abs(diff) > worst:
                worst, worst_alt = abs(diff), alt
        verdict = ("PASS" if ok else "FAIL") if tested else "(below 5 deg)"
        print(f"  {alt:>9} {gowc:>9.4f} {ky:>9.4f} {diff:>+7.2f}%  {verdict}")
    print("  " + "-" * 50)
    print(f"\n  Largest deviation at and above {MIN_TESTED_ALT:.0f} deg: "
          f"{worst:.2f}% (at {worst_alt} deg)  "
          f"({'ALL PASS' if all_pass else 'SOME FAILED'}, "
          f"tolerance {TOLERANCE_PCT:.0f}%)\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
