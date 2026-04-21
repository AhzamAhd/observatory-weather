import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
from datetime import datetime

# ── Connect to database ───────────────────────────────────────────
def get_connection():
    return sqlite3.connect("data/silver/observatory_weather.db")

# ── Color map based on condition ──────────────────────────────────
def get_color(score):
    if score >= 80:
        return "#1D9E75"   # green — excellent
    elif score >= 60:
        return "#378ADD"   # blue — good
    elif score >= 40:
        return "#EF9F27"   # amber — marginal
    else:
        return "#E24B4A"   # red — poor

# ── Chart 1: Bar chart of current scores ─────────────────────────
def plot_bar_chart(df):
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = [get_color(s) for s in df["observation_score"]]
    bars = ax.barh(df["observatory"], df["observation_score"],
                   color=colors, height=0.5)

    # Add score labels on bars
    for bar, score in zip(bars, df["observation_score"]):
        ax.text(bar.get_width() - 3, bar.get_y() + bar.get_height() / 2,
                f"{score}", va="center", ha="right",
                color="white", fontsize=11, fontweight="bold")

    ax.set_xlim(0, 105)
    ax.set_xlabel("Observation Quality Score (0–100)", fontsize=11)
    ax.set_title(f"Observatory Observation Quality — {datetime.utcnow().strftime('%Y-%m-%d')} UTC",
                 fontsize=13, fontweight="bold", pad=15)

    # Legend
    legend = [
        mpatches.Patch(color="#1D9E75", label="Excellent (80–100)"),
        mpatches.Patch(color="#378ADD", label="Good (60–79)"),
        mpatches.Patch(color="#EF9F27", label="Marginal (40–59)"),
        mpatches.Patch(color="#E24B4A", label="Poor (0–39)")
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    os.makedirs("data/gold/charts", exist_ok=True)
    path = "data/gold/charts/scores_bar_chart.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Bar chart saved → {path}")

# ── Chart 2: Weather breakdown per observatory ────────────────────
def plot_weather_breakdown(df):
    fig, axes = plt.subplots(1, 3, figsize=(14, 6))

    names = [n.replace(" Observatory", "").replace(" Telescope", "")
             for n in df["observatory"]]

    # Cloud cover
    axes[0].bar(names, df["cloud_cover_pct"], color="#85B7EB")
    axes[0].set_title("Cloud Cover (%)", fontweight="bold")
    axes[0].set_ylim(0, 100)
    axes[0].axhline(y=50, color="red", linestyle="--", alpha=0.5, linewidth=1)
    axes[0].tick_params(axis="x", rotation=30)

    # Humidity
    axes[1].bar(names, df["humidity_pct"], color="#AFA9EC")
    axes[1].set_title("Humidity (%)", fontweight="bold")
    axes[1].set_ylim(0, 100)
    axes[1].axhline(y=85, color="red", linestyle="--", alpha=0.5, linewidth=1,
                    label="85% threshold")
    axes[1].legend(fontsize=8)
    axes[1].tick_params(axis="x", rotation=30)

    # Wind speed
    axes[2].bar(names, df["wind_speed_ms"], color="#9FE1CB")
    axes[2].set_title("Wind Speed (m/s)", fontweight="bold")
    axes[2].axhline(y=15, color="red", linestyle="--", alpha=0.5, linewidth=1,
                    label="15 m/s threshold")
    axes[2].legend(fontsize=8)
    axes[2].tick_params(axis="x", rotation=30)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle("Atmospheric Conditions by Observatory", fontsize=13,
                 fontweight="bold", y=1.02)

    path = "data/gold/charts/weather_breakdown.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Breakdown chart saved → {path}")

# ── Main runner ───────────────────────────────────────────────────
def main():
    print(f"\n Generating charts — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")

    conn = get_connection()

    df = pd.read_sql("""
        SELECT
            observatory,
            cloud_cover_pct,
            humidity_pct,
            wind_speed_ms,
            temperature_c,
            observation_score,
            condition
        FROM observation_quality
        ORDER BY observation_score DESC
    """, conn)

    conn.close()

    plot_bar_chart(df)
    plot_weather_breakdown(df)

    print("\n All charts saved to data/gold/charts/\n")

if __name__ == "__main__":
    main()