"""
Generate the two data figures for the GOWC methods paper.

fig_ranking.png : nightly-median GOWC vs measured DIMM at Paranal, with rho + CI.
fig_decomp.png  : the MASS/DIMM decomposition as distributions (DIMM total,
                  MASS free-atmosphere, recovered ground layer).

Saves PNGs into tests/ (the .tex sets \\graphicspath to find them there).
Run:  python tests/make_paper_figures.py <out_dir>
"""
import os
import sys
import csv
import math
import statistics
from datetime import datetime, timedelta
import importlib.util

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE

spec = importlib.util.spec_from_file_location(
    "hm", os.path.join(HERE, "hindcast_multiyear.py"))
hm = importlib.util.module_from_spec(spec); spec.loader.exec_module(hm)


def fig_ranking():
    pred = hm.gowc_hourly("Paranal")
    dimm = hm.measured_hourly(hm.SITES["Paranal"]["dimm"], "seeing")
    pn = hm.nightly_medians(pred, hours=dimm); dn = hm.nightly_medians(dimm)
    cn = sorted(set(pn) & set(dn))
    x = [dn[d] for d in cn]; y = [pn[d] for d in cn]
    rho = hm.spearman(y, x); lo, hi = hm.fisher_ci(rho, len(cn))

    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.scatter(x, y, s=9, alpha=0.35, edgecolors="none", color="#2b6cb0")
    lim = [0.4, 3.2]
    ax.plot(lim, lim, "k--", lw=0.8, label="1:1")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lim); ax.set_ylim(lim)
    from matplotlib.ticker import NullFormatter, FixedLocator, FixedFormatter
    ticks = [0.5, 0.7, 1.0, 1.5, 2.0, 3.0]
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(FixedLocator(ticks))
        axis.set_major_formatter(FixedFormatter([str(t) for t in ticks]))
        axis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Measured DIMM seeing, nightly median (arcsec, log scale)")
    ax.set_ylabel("GOWC seeing, nightly median (arcsec, log scale)")
    ax.set_title(f"Paranal, {len(cn)} nights\n"
                 rf"Spearman $\rho={rho:+.2f}$ [{lo:+.2f}, {hi:+.2f}]",
                 fontsize=10)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_aspect("equal")
    fig.tight_layout()
    p = os.path.join(OUT, "fig_ranking.png")
    fig.savefig(p, dpi=160); plt.close(fig)
    # Dynamic-range compression: OLS slope of log(model) on log(DIMM), and the
    # ratio of the log-seeing standard deviations (paper Table 4 caption).
    lx = [math.log10(v) for v in x if v > 0]
    ly = [math.log10(w) for v, w in zip(x, y) if v > 0 and w > 0]
    mx = sum(lx) / len(lx); my = sum(ly) / len(ly)
    slope = (sum((a - mx) * (b - my) for a, b in zip(lx, ly))
             / sum((a - mx) ** 2 for a in lx))
    sdx = statistics.pstdev(lx); sdy = statistics.pstdev(ly)
    print(f"wrote {p}  (N={len(cn)}, rho={rho:+.3f}, "
          f"OLS slope={slope:.2f}, sd-ratio={sdy/sdx:.2f})")


def fig_decomp():
    # Use the MASS/DIMM archive (May-Aug window with both instruments)
    mass = hm.SITES["Paranal"]["mass"]
    dimm_f = os.path.join(HERE, "dimm_paranal_2026-05_08.csv")
    # parse both to hourly, match per timestamp
    def parse(path, key):
        rows = []
        with open(path, newline="") as f:
            hdr = None
            for r in csv.reader(f):
                if not r or all(not c.strip() for c in r) or r[0].startswith("#"):
                    continue
                if hdr is None:
                    hdr = [c.lower() for c in r]
                    ti = next(i for i, c in enumerate(hdr) if "date" in c)
                    vi = next(i for i, c in enumerate(hdr) if key in c)
                    continue
                try:
                    t = datetime.fromisoformat(r[ti][:19]); v = float(r[vi])
                except (ValueError, IndexError):
                    continue
                if v > 0:
                    rows.append((t, v))
        return rows
    free = parse(mass, "free atmosphere"); free.sort()
    dimm = parse(dimm_f, "dimm seeing"); dimm.sort()
    # nearest-time match within 120s
    fmap = {}
    j = 0
    fl = free
    for t, v in dimm:
        while j + 1 < len(fl) and abs((fl[j + 1][0] - t).total_seconds()) <= \
                abs((fl[j][0] - t).total_seconds()):
            j += 1
        if j < len(fl) and abs((fl[j][0] - t).total_seconds()) <= 120:
            fmap[t] = (v, fl[j][1])
    tot = [a for a, b in fmap.values()]
    frv = [b for a, b in fmap.values()]
    gl = [math.sqrt(a**2 - b**2) for a, b in fmap.values() if a > b]

    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    bins = [i * 0.05 for i in range(0, 40)]
    ax.hist(tot, bins=bins, alpha=0.55, label=f"DIMM total (med {statistics.median(tot):.2f}\")",
            color="#e2704a")
    ax.hist(frv, bins=bins, alpha=0.55, label=f"MASS free-atm (med {statistics.median(frv):.2f}\")",
            color="#2b6cb0")
    ax.hist(gl, bins=bins, alpha=0.55, label=f"Ground layer (med {statistics.median(gl):.2f}\")",
            color="#1d9e75")
    ax.set_xlabel("Seeing (arcsec)")
    ax.set_ylabel("Matched samples (native ASM cadence)")
    ax.set_title(f"Paranal MASS/DIMM decomposition (N={len(fmap)})", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.set_xlim(0, 1.8)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_decomp.png")
    fig.savefig(p, dpi=160); plt.close(fig)
    print(f"wrote {p}  (N={len(fmap)})")


def fig_pwv():
    """GOWC model-column PWV (corrected to the model terrain, S3.3) vs the ESO
    LHATPRO radiometer at Paranal, nightly medians. The strongest correlation in
    the paper (rho ~ +0.95); the +40% wet bias is visible as the offset above 1:1."""
    import importlib.util as _u
    spec = _u.spec_from_file_location(
        "vp", os.path.join(HERE, "validate_pwv_lhatpro.py"))
    vp = _u.module_from_spec(spec); spec.loader.exec_module(vp)

    # Corrected column: residual to the model-cell terrain (paper S3.3), which at
    # Paranal (h_site 2635 m, h_model ~2617 m) is a ~0.99 factor.
    h = vp.fetch_model_pwv()
    H_MODEL = 2617.0
    corr = {}
    for i, ts in enumerate(h["time"]):
        col = h["total_column_integrated_water_vapour"][i]
        if col is None:
            continue
        pwv = col * math.exp(-max(0.0, vp.ALT - H_MODEL) / vp.HW)
        corr[datetime.fromisoformat(ts[:19])] = pwv
    lhat = vp.fetch_lhatpro()
    model = vp.nightly(corr, hours=lhat)
    meas = vp.nightly(lhat)
    cn = sorted(set(model) & set(meas))
    x = [meas[d] for d in cn]; y = [model[d] for d in cn]
    rho = vp.spearman(y, x); lo, hi = vp.fisher_ci(rho, len(cn))
    bias = statistics.median(y) / statistics.median(x)

    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.scatter(x, y, s=9, alpha=0.35, edgecolors="none", color="#1d9e75")
    lim = [0.3, 20.0]
    ax.plot(lim, lim, "k--", lw=0.8, label="1:1")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lim); ax.set_ylim(lim)
    from matplotlib.ticker import NullFormatter, FixedLocator, FixedFormatter
    ticks = [0.5, 1, 2, 5, 10, 20]
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(FixedLocator(ticks))
        axis.set_major_formatter(FixedFormatter([str(t) for t in ticks]))
        axis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("LHATPRO PWV, nightly median (mm, log scale)")
    ax.set_ylabel("GOWC model PWV, nightly median (mm, log scale)")
    ax.set_title(f"Paranal, {len(cn)} nights\n"
                 rf"Spearman $\rho={rho:+.2f}$ [{lo:+.2f}, {hi:+.2f}]",
                 fontsize=10)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_aspect("equal")
    fig.tight_layout()
    p = os.path.join(OUT, "fig_pwv.png")
    fig.savefig(p, dpi=160); plt.close(fig)
    print(f"wrote {p}  (N={len(cn)}, rho={rho:+.3f}, bias={bias:.2f}x)")


if __name__ == "__main__":
    fig_ranking()
    fig_decomp()
    fig_pwv()
