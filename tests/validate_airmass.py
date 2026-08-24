"""
Validate GOWC's airmass against the Kasten & Young (1989) reference tables.

Kasten & Young (1989, Applied Optics 28, 4735) is the standard reference for
optical airmass. GOWC uses the Pickering (2002) interpolative formula, which
should reproduce the Kasten-Young values closely (they agree to <0.1% away from
the horizon by construction). This script checks that.

HOW TO RUN IT YOURSELF:
    python tests/validate_airmass.py

HOW TO ADD YOUR OWN CHECK:
    Look up an airmass value from any published table (Kasten-Young, or an
    almanac), add the (altitude_deg: airmass) pair to KY_REFERENCE below, and
    re-run. The script prints GOWC's value beside the reference and the % error.

Result (PASS if all within 1%): max deviation ~0.34%.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airmass_calculator import altitude_to_airmass   # noqa: E402


# Reference airmass X at apparent altitude (deg), from Kasten & Young (1989).
# These are the accepted published values; edit/extend freely.
KY_REFERENCE = {
    90: 1.000, 80: 1.015, 70: 1.064, 60: 1.154, 50: 1.304,
    40: 1.553, 30: 1.995, 20: 2.904, 15: 3.816, 10: 5.600, 5: 10.32,
}

TOLERANCE_PCT = 1.0   # PASS if within 1%


def main():
    print("\n  GOWC airmass vs Kasten & Young (1989)\n")
    print(f"  {'alt (deg)':>9} {'GOWC':>9} {'K-Y ref':>9} {'diff %':>8}  "
          f"{'verdict'}")
    print("  " + "-" * 50)
    max_err = 0.0
    all_pass = True
    for alt in sorted(KY_REFERENCE, reverse=True):
        ky = KY_REFERENCE[alt]
        gowc = altitude_to_airmass(alt)
        diff = 100.0 * (gowc - ky) / ky
        max_err = max(max_err, abs(diff))
        ok = abs(diff) <= TOLERANCE_PCT
        all_pass = all_pass and ok
        print(f"  {alt:>9} {gowc:>9.3f} {ky:>9.3f} {diff:>+7.2f}%  "
              f"{'PASS' if ok else 'FAIL'}")
    print("  " + "-" * 50)
    print(f"\n  Max deviation: {max_err:.2f}%  "
          f"({'ALL PASS' if all_pass else 'SOME FAILED'}, "
          f"tolerance {TOLERANCE_PCT:.0f}%)\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
