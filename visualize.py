import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
from datetime import datetime

def get_connection():
    return sqlite3.connect("data/silver/observatory_weather.db")

def get_color(score):
    if score >= 80:   return "#1D9E75"
    elif score >= 60: return "#378ADD"
    elif score >= 40: return "#EF9F27"
    else:             return "#E24B4A"

def plot_bar_chart(df):
    fig, ax = plt.subplots(figsize=(12, max(8, len(df) * 0.35)))
    colors  = [get_color(s) for s in df["observation_score"]]
    bars    = ax.barh(df["observatory"], df["observation_score"],
                      color=colors, height=0.6)
    for bar, score in zip(bars, df["observation_score"]):
        ax.text(bar.get_width() - 2, bar.get_y() + bar.get_height() / 2,
                f"{score}", va="center", ha="right",
                color="white", fontsize=8, fontweight="bold")
    ax.set_xlim(0, 105)
    ax.set_xlabel("Observation Quality Score (0–100)", fontsize=11)
    ax.set_title(
        f"Observatory Observation Quality — {datetime.utcnow().strftime('%Y-%m-%d')} UTC",
        fontsize=13, fontweight="bold", pad=15)
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
    ax.tick_params(axis="y", labelsize=7)
    os.makedirs("data/gold/charts", exist_ok=True)
    path = "data/gold/charts/scores_bar_chart.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Bar chart saved → {path}")

def plot_weather_breakdown(df):
    top20 = df.head(20)
    names = [n.replace(" Observatory", "").replace(" Telescope", "")
             .replace(" Array", "")[:30]
             for n in top20["observatory"]]
    fig, axes = plt.subplots(1, 3, figsize=(16, 8))
    axes[0].barh(names, top20["cloud_cover_pct"], color="#85B7EB")
    axes[0].set_title("Cloud Cover (%)", fontweight="bold")
    axes[0].set_xlim(0, 100)
    axes[0].axvline(x=50, color="red", linestyle="--", alpha=0.5)

    axes[1].barh(names, top20["humidity_pct"], color="#AFA9EC")
    axes[1].set_title("Humidity (%)", fontweight="bold")
    axes[1].set_xlim(0, 100)
    axes[1].axvline(x=85, color="red", linestyle="--", alpha=0.5, label="85% threshold")
    axes[1].legend(fontsize=8)

    axes[2].barh(names, top20["wind_speed_ms"], color="#9FE1CB")
    axes[2].set_title("Wind Speed (m/s)", fontweight="bold")
    axes[2].axvline(x=15, color="red", linestyle="--", alpha=0.5, label="15 m/s threshold")
    axes[2].legend(fontsize=8)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="y", labelsize=8)

    fig.suptitle("Top 20 Observatories — Atmospheric Conditions",
                 fontsize=13, fontweight="bold")
    path = "data/gold/charts/weather_breakdown.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Breakdown chart saved → {path}")

def main():
    print(f"\n Generating charts — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")
    conn = get_connection()
    df   = pd.read_sql("""
        SELECT observatory, cloud_cover_pct, humidity_pct,
               wind_speed_ms, temperature_c, observation_score, condition
        FROM observation_quality
        ORDER BY observation_score DESC
    """, conn)
    conn.close()
    plot_bar_chart(df)
    plot_weather_breakdown(df)
    print("\n All charts saved to data/gold/charts/\n")

if __name__ == "__main__":
    main()