"""
GOWC vs ING SIGNAL across the m x X grid (V band, 100 s, sky D, ext 0.12,
seeing 1.0). SIGNAL values are hand-run from the browser ETC (no scriptable
interface); GOWC values are recomputed here. Emits the residual table (LaTeX
rows) and summary statistics for the paper appendix.

Run:  python tests/snr_grid_compare.py
"""
import sys
import os
import math
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from snr_calculator import calculate_snr             # noqa: E402
from instruments import get_instrument_config         # noqa: E402


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

INSTR = {
    "WHT/ACAM": (ACAM, dict(wavelength_nm=550.0, bandwidth_nm=86.0)),
    "INT/WFC":  (WFC,  dict()),
}

# Hand-run SIGNAL SNRs, keyed (instrument, magnitude, airmass).
# None where not yet supplied.
SIGNAL = {
    ("WHT/ACAM", 16, 1.0): 1280.00,
    ("WHT/ACAM", 18, 1.0): 484.81,
    ("WHT/ACAM", 20, 1.0): 152.66,
    ("WHT/ACAM", 22, 1.0): 33.15,
    ("WHT/ACAM", 16, 1.5): 1245.11,
    ("WHT/ACAM", 18, 1.5): 471.58,
    ("WHT/ACAM", 20, 1.5): 148.48,
    ("WHT/ACAM", 22, 1.5): 32.23,
    ("INT/WFC", 16, 1.0): 750.19,
    ("INT/WFC", 18, 1.0): 283.95,
    ("INT/WFC", 20, 1.0): 89.20,
    ("INT/WFC", 22, 1.0): 19.31,
    ("INT/WFC", 16, 1.5): 729.74,
    ("INT/WFC", 18, 1.5): 276.19,
    ("INT/WFC", 20, 1.5): 86.73,
    ("INT/WFC", 22, 1.5): 18.77,
}


def gowc_snr(specs, m, X, extra):
    r = calculate_snr(
        telescope_specs=specs, object_magnitude=float(m), exposure_time_s=100,
        sky_brightness_mag=21.50, seeing_arcsec=1.0,
        object_altitude_deg=_alt_from_airmass(X), filter_band="V",
        extinction_coeff=0.12, **extra)
    return r["snr"]


def main():
    print("\n  GOWC vs SIGNAL SNR grid (V, 100 s, sky D, ext 0.12, seeing 1.0)\n")
    print(f"  {'inst':9} {'m':>3} {'X':>4} {'GOWC':>9} {'SIGNAL':>9} "
          f"{'ratio':>7} {'%diff':>7}")
    print("  " + "-" * 52)
    ratios = []
    tex = []
    for inst, (specs, extra) in INSTR.items():
        for X in (1.0, 1.5):
            for m in (16, 18, 20, 22):
                sig = SIGNAL.get((inst, m, X))
                g = gowc_snr(specs, m, X, extra)
                if sig is None:
                    print(f"  {inst:9} {m:>3} {X:>4.1f} {g:>9.2f} "
                          f"{'--':>9} {'--':>7} {'--':>7}")
                    tex.append(f"{inst} & {m} & {X:.1f} & {g:.1f} & -- & -- \\\\")
                    continue
                r = g / sig
                pd = (r - 1) * 100
                ratios.append(r)
                print(f"  {inst:9} {m:>3} {X:>4.1f} {g:>9.2f} {sig:>9.2f} "
                      f"{r:>7.3f} {pd:>+7.1f}")
                tex.append(f"{inst} & {m} & {X:.1f} & {g:.1f} & {sig:.1f} "
                           f"& {pd:+.1f}\\% \\\\")
    print("  " + "-" * 52)
    n = len(ratios)
    med = statistics.median(ratios)
    mad = statistics.median([abs(r - med) for r in ratios])
    worst = max(ratios, key=lambda r: abs(r - 1))
    print(f"\n  N points compared     = {n}")
    print(f"  median GOWC/SIGNAL    = {med:.3f}  ({(med-1)*100:+.1f}%)")
    print(f"  median |%diff|        = "
          f"{statistics.median([abs((r-1)*100) for r in ratios]):.1f}%")
    print(f"  worst |%diff|         = {abs((worst-1)*100):.1f}% "
          f"(ratio {worst:.3f})")
    print(f"  all within 10%%?       = "
          f"{all(abs(r-1) <= 0.10 for r in ratios)}")
    print("\n  --- LaTeX rows ---")
    for t in tex:
        print("  " + t)
    print()


if __name__ == "__main__":
    main()
