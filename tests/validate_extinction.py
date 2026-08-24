"""
Validate GOWC's atmospheric-extinction coefficients against published site
values.

Extinction coefficients k (mag/airmass) are measured and published for major
observatories. GOWC anchors its coefficients to La Palma (King 1985; ING
monitoring) and scales them with site altitude. This script checks GOWC's k
against published values for a few real sites.

HOW TO RUN IT YOURSELF:
    python tests/validate_extinction.py

HOW TO ADD YOUR OWN CHECK:
    Find published mean extinction coefficients for a site (e.g. from an
    observatory's site-monitoring page or a photometry paper), add an entry to
    PUBLISHED below with the site altitude and per-band values, and re-run.

Note: real extinction varies night to night (aerosols, dust), so agreement to
a few 0.01 mag/airmass is expected and good. La Palma agrees to ~0.002 because
GOWC's reference is anchored there; other sites are looser, which is honest.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airmass_calculator import extinction_coefficient   # noqa: E402


# Published mean extinction coefficients (mag/airmass) by band, per site.
# La Palma: King (1985) / ING. Paranal: ESO site data. Edit/extend freely.
PUBLISHED = {
    "La Palma (ORM, 2360 m)": {
        "altitude_m": 2360,
        "coeff": {"U": 0.46, "B": 0.22, "V": 0.12, "R": 0.09, "I": 0.05},
        "source": "King (1985); ING site monitoring",
    },
    "Paranal (ESO, 2635 m)": {
        "altitude_m": 2635,
        "coeff": {"U": 0.42, "B": 0.21, "V": 0.11, "R": 0.08, "I": 0.04},
        "source": "ESO Paranal site data",
    },
}

TOLERANCE = 0.03   # mag/airmass; PASS if within this of the published value


def main():
    print("\n  GOWC extinction coefficients vs published site values\n")
    all_pass = True
    for site, d in PUBLISHED.items():
        print(f"  {site}   [{d['source']}]")
        print(f"    {'band':>4} {'GOWC':>7} {'pub':>7} {'diff':>7}  verdict")
        for band, ref in d["coeff"].items():
            g = extinction_coefficient(d["altitude_m"], band)
            diff = g - ref
            ok = abs(diff) <= TOLERANCE
            all_pass = all_pass and ok
            print(f"    {band:>4} {g:>7.3f} {ref:>7.3f} {diff:>+7.3f}  "
                  f"{'PASS' if ok else 'FAIL'}")
        print()
    print("  " + "-" * 46)
    print(f"  {'ALL PASS' if all_pass else 'SOME FAILED'} "
          f"(tolerance {TOLERANCE} mag/airmass)\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
