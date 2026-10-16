"""
Generate the GOWC system-architecture figure for the methods paper.

A left-to-right data-flow diagram: external inputs -> ingest -> database ->
physics/planning core -> user surfaces, with the scheduled job and the live
site-monitor bypass shown. Pure matplotlib (no extra deps), saved as a PNG next
to the .tex.

Run:  python tests/make_arch_figure.py <out_dir>
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

BLUE = "#2b6cb0"; GREY = "#4a5568"; GREEN = "#1d9e75"; SAND = "#b7791f"
INK = "#1a202c"


def box(ax, x, y, w, h, title, sub="", fc="#ffffff", ec=GREY, tc=INK):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.3, edgecolor=ec, facecolor=fc, mutation_aspect=1))
    ax.text(x + w / 2, y + h * (0.62 if sub else 0.5), title,
            ha="center", va="center", fontsize=9.2, weight="bold", color=tc)
    if sub:
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                fontsize=7.2, color=GREY)


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", lw=1.4, ls="-"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13,
        linewidth=lw, color=color, linestyle=ls,
        connectionstyle="arc3,rad=0"))


def main():
    fig, ax = plt.subplots(figsize=(9.2, 4.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    ax.axis("off")

    # Column x-centres
    box(ax, 0.15, 2.05, 1.7, 1.1, "Open-Meteo API",
        "surface +\n850/700/600/\n500/250 hPa", fc="#eef4fb", ec=BLUE, tc=BLUE)
    box(ax, 2.25, 2.05, 1.7, 1.1, "fetch_weather.py",
        "raw JSON\n(per site)", fc="#ffffff")
    box(ax, 4.35, 2.05, 1.7, 1.1, "Supabase\nPostgres",
        "weather_readings\n+ history", fc="#f0fff7", ec=GREEN, tc=GREEN)
    box(ax, 6.45, 2.05, 1.75, 1.1, "Physics core",
        "atmospheric.py\nseeing/PWV/ext.\ninstruments+SNR", fc="#ffffff")
    box(ax, 8.35, 3.05, 1.55, 1.05, "Dashboard",
        "Streamlit UI\n(2,642 sites)", fc="#fffaf0", ec=SAND, tc=SAND)
    box(ax, 8.35, 1.05, 1.55, 1.05, "REST API",
        "api.py\n(JSON)", fc="#fffaf0", ec=SAND, tc=SAND)

    # Scheduler above ingest
    box(ax, 2.25, 3.75, 1.7, 0.7, "GitHub Actions",
        "scheduled fetch", fc="#f7f7f9", ec=GREY)
    arrow(ax, 3.1, 3.75, 3.1, 3.17, color=GREY, ls=(0, (4, 2)))

    # Live site-monitor bypass below
    box(ax, 4.35, 0.25, 3.55, 0.7, "Live site monitors (ESO ASM, MKWC)",
        "DIMM / MASS / LHATPRO — measured value shown directly",
        fc="#eef4fb", ec=BLUE, tc=BLUE)

    # Main flow arrows
    arrow(ax, 1.85, 2.6, 2.25, 2.6, color=BLUE)
    arrow(ax, 3.95, 2.6, 4.35, 2.6)
    arrow(ax, 6.05, 2.6, 6.45, 2.6, color=GREEN)
    arrow(ax, 8.2, 2.75, 8.55, 3.05)      # core -> dashboard
    arrow(ax, 8.2, 2.45, 8.55, 2.1)       # core -> API

    # Live-monitor bypass into the user surfaces (skips the model)
    arrow(ax, 7.9, 0.6, 9.12, 0.6, color=BLUE)
    arrow(ax, 9.12, 0.6, 9.12, 1.05, color=BLUE)

    ax.text(5.0, 4.75, "GOWC data flow: forecast ingest → store → physics → user; "
            "measured monitors bypass the model",
            ha="center", va="center", fontsize=9.5, style="italic", color=INK)

    fig.tight_layout()
    p = os.path.join(OUT, "fig_arch.png")
    fig.savefig(p, dpi=170, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
