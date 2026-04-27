import json
import pandas as pd
from datetime import datetime
from db import get_connection, query_df, fetch_one
from observing_window import get_all_windows
from peak_time import get_all_peak_times
from telescope_efficiency import get_all_efficiency_scores
from atmospheric import get_full_atmospheric_analysis

def precompute_all():
    print(f"\n Pre-computing dashboard data — "
          f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n")

    conn = get_connection()
    cur  = conn.cursor()

    def save(key, data):
        cur.execute("""
            INSERT INTO precomputed
                (key, value, computed_at)
            VALUES (%s, %s::jsonb, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value       = EXCLUDED.value,
                computed_at = EXCLUDED.computed_at
        """, (key, json.dumps(data, default=str)))
        conn.commit()
        print(f"  Saved → {key}")

    # ── Observing windows ─────────────────────────────────
    print("  Computing observing windows...")
    win = get_all_windows()
    if not win.empty:
        save("observing_windows", win.to_dict("records"))

    # ── Peak times ────────────────────────────────────────
    print("  Computing peak times...")
    peak = get_all_peak_times()
    if not peak.empty:
        save("peak_times", peak.to_dict("records"))

    # ── Atmospheric analysis ──────────────────────────────
    print("  Computing atmospheric analysis...")
    df = query_df("""
        SELECT o.name AS observatory, o.country,
               o.altitude_m, o.latitude, o.longitude,
               w.temperature_c, w.wind_speed_ms,
               w.humidity_pct, w.surface_pressure,
               w.jet_stream_ms,
               ROUND(GREATEST(0,
                   100 - (w.cloud_cover_pct * 0.50)
                   - (CASE WHEN w.humidity_pct > 85
                      THEN (w.humidity_pct - 85) * 2.0
                      ELSE 0 END)
                   - (CASE WHEN w.wind_speed_ms > 15
                      THEN (w.wind_speed_ms - 15) * 2.0
                      ELSE 0 END)
               )::numeric, 1) AS weather_score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
    """)

    atm_results = []
    for _, row in df.iterrows():
        atm = get_full_atmospheric_analysis({
            "temperature_c":    row["temperature_c"],
            "wind_speed_ms":    row["wind_speed_ms"],
            "humidity_pct":     row["humidity_pct"],
            "altitude_m":       row["altitude_m"],
            "surface_pressure": row.get("surface_pressure"),
            "jet_stream_ms":    row.get("jet_stream_ms"),
            "latitude":         row["latitude"]
        })
        atm_results.append({
            "observatory":   row["observatory"],
            "country":       row["country"],
            "altitude_m":    row["altitude_m"],
            "weather_score": float(row["weather_score"]),
            **atm
        })
    save("atmospheric", atm_results)

    # ── Efficiency scores ─────────────────────────────────
    for tel_type in ["optical", "infrared", "radio"]:
        print(f"  Computing {tel_type} efficiency...")
        eff = get_all_efficiency_scores(tel_type)
        if not eff.empty:
            save(
                f"efficiency_{tel_type}",
                eff.to_dict("records")
            )

    cur.close()
    conn.close()
    print("\n  ✅ Pre-computation complete.\n")

def load_precomputed(key):
    row = fetch_one(
        "SELECT value FROM precomputed WHERE key = %s",
        [key]
    )
    if row:
        value = row["value"]
        if isinstance(value, str):
            return pd.DataFrame(json.loads(value))
        return pd.DataFrame(value)
    return pd.DataFrame()

if __name__ == "__main__":
    precompute_all()