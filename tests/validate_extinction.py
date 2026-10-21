"""
Validate GOWC's atmospheric-extinction coefficients against published site
values.

GOWC sets its reference coefficients to representative values for the Roque de
los Muchachos Observatory, La Palma (cf. King 1985), and scales them with site
altitude. La Palma agreement is therefore by construction. The independent
check is Paranal, against the broadband UBVRI extinction coefficients ESO
Quality Control derives from FORS1 standard-star photometry each observing
period:

    https://www.eso.org/qc/FORS1/qc/photcoeff/photcoeffs_fors1.html
    (accessed 2026 October)

The page lists one value per period (P73a 2004 to P82 2009; from P79 one per
CCD chip, and none in U, B, V for P81-P82). We take the median over every
tabulated value, transcribed below, and also print the range, since extinction
varies strongly from period to period.

HOW TO RUN IT YOURSELF:
    python tests/validate_extinction.py
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airmass_calculator import extinction_coefficient   # noqa: E402

# Representative ORM values the reference coefficients were set to.
LA_PALMA = {"altitude_m": 2360,
            "coeff": {"U": 0.46, "B": 0.22, "V": 0.12, "R": 0.09, "I": 0.05}}

# ESO QC FORS1 per-period extinction coefficients (mag/airmass), transcribed
# from the page above in its order: P82 (chips 1, 2), P81 (1, 2), P80 (1, 2),
# P79 (1, 2), P78, P77, P76, P75b, P75a, P74, P73b, P73a.
_NA = None
ESO_FORS1_QC = {
    "U": [_NA, _NA, _NA, _NA, 0.440, 0.465, 0.447, 0.470,
          0.500, 0.442, 0.451, 0.425, 0.442, 0.297, 0.278, 0.650],
    "B": [_NA, _NA, _NA, _NA, 0.262, 0.260, 0.241, 0.316,
          0.312, 0.200, 0.286, 0.268, 0.232, 0.145, 0.208, 0.346],
    "V": [_NA, _NA, _NA, _NA, 0.131, 0.099, 0.112, 0.158,
          0.175, 0.103, 0.125, 0.147, 0.132, 0.083, 0.094, 0.223],
    "R": [0.073, 0.103, 0.065, 0.081, 0.111, 0.089, 0.087, 0.111,
          0.132, 0.068, 0.062, 0.105, 0.079, 0.087, 0.037, 0.150],
    "I": [0.057, 0.050, 0.046, 0.031, 0.084, 0.089, 0.027, 0.037,
          0.109, 0.024, 0.036, 0.067, 0.046, 0.003, 0.025, 0.168],
}
PARANAL_M = 2635
# Extinction varies strongly between periods (e.g. 0.08-0.22 in V), so the
# test is whether GOWC lies inside the published period-to-period range; the
# offset from the median is printed alongside.


def main():
    all_pass = True
    print("\n  La Palma (ORM, 2360 m): representative values the reference "
          "coefficients were set to (by construction)")
    print(f"    {'band':>4} {'GOWC':>7} {'set':>7} {'diff':>7}")
    for band, ref in LA_PALMA["coeff"].items():
        g = extinction_coefficient(LA_PALMA["altitude_m"], band)
        print(f"    {band:>4} {g:>7.3f} {ref:>7.3f} {g - ref:>+7.3f}")

    print(f"\n  Paranal ({PARANAL_M} m) vs ESO QC FORS1 broadband coefficients "
          "(median over periods)")
    print(f"    {'band':>4} {'GOWC':>7} {'median':>7} {'N':>3} "
          f"{'range':>13} {'diff':>7}  verdict")
    for band, vals in ESO_FORS1_QC.items():
        v = [x for x in vals if x is not None]
        med = statistics.median(v)
        g = extinction_coefficient(PARANAL_M, band)
        ok = min(v) <= g <= max(v)
        all_pass = all_pass and ok
        print(f"    {band:>4} {g:>7.3f} {med:>7.3f} {len(v):>3} "
              f"{min(v):>6.3f}-{max(v):<6.3f} {g - med:>+7.3f}  "
              f"{'PASS (within range)' if ok else 'FAIL (outside range)'}")
    print("\n  " + "-" * 46)
    print(f"  {'ALL PASS' if all_pass else 'SOME FAILED'} "
          "(GOWC inside the ESO period-to-period range in every band)\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
