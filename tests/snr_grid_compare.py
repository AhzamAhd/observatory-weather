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


import snr_calculator                                   # noqa: E402


def _alt_from_airmass(x):
    """Altitude (deg) whose Pickering (2002) airmass -- GOWC's definition -- is
    exactly X (bisection), so the grid is evaluated at SIGNAL's airmass."""
    lo, hi = 1.0, 90.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if snr_calculator._pickering_airmass(mid) > x:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# Both instruments come straight from GOWC's catalogue (instruments.py): the
# configuration an observer actually gets is the one benchmarked.
ACAM = get_instrument_config(
    "William Herschel Telescope (WHT)", "ACAM (imaging)", "V (visual)")
WFC = get_instrument_config(
    "Isaac Newton Telescope (INT)", "WFC (Wide Field Camera)", "V (visual)")

INSTR = {
    "WHT/ACAM": (ACAM, dict()),
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


def no_scintillation_residuals():
    """Diagnostic for the appendix: residuals with GOWC's scintillation term
    switched off, isolating the throughput/normalisation offset."""
    real = snr_calculator.scintillation_sigma
    snr_calculator.scintillation_sigma = lambda *a, **k: 0.0
    try:
        print("\n  Residuals with scintillation OFF (GOWC/SIGNAL - 1), m = 16..22:")
        for inst, (specs, extra) in INSTR.items():
            for X in (1.0, 1.5):
                row = [f"{(gowc_snr(specs, m, X, extra) / SIGNAL[(inst, m, X)] - 1) * 100:+.1f}%"
                       for m in (16, 18, 20, 22)]
                print(f"    {inst:9} X={X:.1f}: " + "  ".join(row))
    finally:
        snr_calculator.scintillation_sigma = real


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
    no_scintillation_residuals()
    print()


if __name__ == "__main__":
    main()
