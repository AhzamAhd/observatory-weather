"""
Generate the two data figures for the GOWC methods paper.

fig_ranking.png : nightly-median GOWC vs measured DIMM at Paranal, with rho + CI.
fig_decomp.png  : the MASS/DIMM decomposition as distributions (DIMM total,
                  MASS free-atmosphere, recovered ground layer).

Saves PNGs into the scratchpad next to the .tex so \includegraphics finds them.
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
    pn = hm.nightly_medians(pred); dn = hm.nightly_medians(dimm)
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
    ax.set_xlabel("Measured DIMM seeing, nightly median (arcsec)")
    ax.set_ylabel("GOWC seeing, nightly median (arcsec)")
    ax.set_title(f"Paranal, {len(cn)} nights\n"
                 rf"Spearman $\rho={rho:+.2f}$ [{lo:+.2f}, {hi:+.2f}]",
                 fontsize=10)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_aspect("equal")
    fig.tight_layout()
    p = os.path.join(OUT, "fig_ranking.png")
    fig.savefig(p, dpi=160); plt.close(fig)
    print(f"wrote {p}  (N={len(cn)}, rho={rho:+.3f})")


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
    ax.set_ylabel("Hourly-matched samples")
    ax.set_title(f"Paranal MASS/DIMM decomposition (N={len(fmap)})", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.set_xlim(0, 1.8)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_decomp.png")
    fig.savefig(p, dpi=160); plt.close(fig)
    print(f"wrote {p}  (N={len(fmap)})")


if __name__ == "__main__":
    fig_ranking()
    fig_decomp()
