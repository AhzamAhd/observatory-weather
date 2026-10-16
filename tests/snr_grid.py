"""
GOWC SNR across an m x t x X grid, for comparison against ING SIGNAL.

Produces the GOWC column of the validation grid; the SIGNAL column is filled in
by hand from the browser ETC (it has no scriptable interface). Two of the rows
(ACAM m=20/t=100/X=1.0 and WFC m=20/t=100/X=1.0) reproduce the anchors already in
Table 2, as a consistency check.

Run:  python tests/snr_grid.py
"""
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snr_calculator import calculate_snr            # noqa: E402
from instruments import get_instrument_config        # noqa: E402


def _alt_from_airmass(x):
    return math.degrees(math.asin(min(1.0, 1.0 / x)))


def _acam_specs():
    area_m2 = 12.47
    aperture = math.sqrt(area_m2 / math.pi) * 2
    return {
        "aperture_m": aperture, "pixel_scale": 0.25, "read_noise": 3.2,
        "dark_current": 0.0, "quantum_efficiency": 0.85,
        "throughput": 0.72 * 0.71, "obstruction": 0.0,
        "full_well_e": None, "type": "optical",
    }


ACAM = _acam_specs()
WFC = get_instrument_config(
    "Isaac Newton Telescope (INT)", "WFC (Wide Field Camera)", "V (visual)")

# Grid: (instrument label, specs, extra kwargs)
INSTR = [
    ("WHT/ACAM", ACAM, dict(wavelength_nm=550.0, bandwidth_nm=86.0)),
    ("INT/WFC",  WFC,  dict()),
]

MAGS = [16, 18, 20, 22]
EXPS = [100]          # keep t fixed at the anchor value to isolate m and X
AIRMASSES = [1.0, 1.5]


def gowc_snr(specs, m, t, X, extra):
    r = calculate_snr(
        telescope_specs=specs,
        object_magnitude=float(m),
        exposure_time_s=t,
        sky_brightness_mag=21.50,
        seeing_arcsec=1.0,
        object_altitude_deg=_alt_from_airmass(X),
        filter_band="V",
        extinction_coeff=0.12,
        **extra,
    )
    return r["snr"], r["source_counts"]


def main():
    print("\n  GOWC SNR grid (V band, sky=21.50, seeing 1.0\", ext 0.12)\n")
    print(f"  {'#':>2}  {'inst':9} {'m':>3} {'t(s)':>5} {'X':>4} "
          f"{'GOWC_SNR':>9} {'GOWC_obj':>10}   SIGNAL_SNR")
    print("  " + "-" * 66)
    i = 0
    for label, specs, extra in INSTR:
        for X in AIRMASSES:
            for m in MAGS:
                for t in EXPS:
                    i += 1
                    snr, obj = gowc_snr(specs, m, t, X, extra)
                    anchor = ""
                    if label == "WHT/ACAM" and m == 20 and X == 1.0:
                        anchor = "  (anchor ~150.56)"
                    if label == "INT/WFC" and m == 20 and X == 1.0:
                        anchor = "  (anchor ~89.20)"
                    print(f"  {i:>2}  {label:9} {m:>3} {t:>5} {X:>4.1f} "
                          f"{snr:>9.2f} {obj:>10.1f}   __________{anchor}")
    print("  " + "-" * 66)
    print("\n  Fill the SIGNAL_SNR column from https://astro.ing.iac.es/signal/")
    print("  (point source, band V, sky 'D', extinction 0.12, seeing 1.0).\n")


if __name__ == "__main__":
    main()
