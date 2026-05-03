import time

print("Testing load times...\n")

start = time.time()
from db import query_df
df = query_df("""
    SELECT
        o.name AS observatory,
        o.country,
        o.latitude,
        o.longitude,
        o.altitude_m,
        w.cloud_cover_pct,
        w.humidity_pct,
        w.wind_speed_ms,
        w.temperature_c,
        w.surface_pressure,
        w.jet_stream_ms,
        ROUND(GREATEST(0,
            100
            - (w.cloud_cover_pct * 0.50)
            - (CASE WHEN w.humidity_pct > 85
               THEN (w.humidity_pct - 85) * 2.0
               ELSE 0 END)
            - (CASE WHEN w.wind_speed_ms > 15
               THEN (w.wind_speed_ms - 15) * 2.0
               ELSE 0 END)
        )::numeric, 1) AS observation_score
    FROM weather_readings w
    JOIN observatories o ON w.observatory_id = o.id
    WHERE w.fetch_date = (
        SELECT MAX(fetch_date) FROM weather_readings
    )
    ORDER BY observation_score DESC
    LIMIT 300
""")
print(f"load_data:           {time.time()-start:.2f}s"
      f" — {len(df)} rows")

start = time.time()
from precompute import load_precomputed
win = load_precomputed("observing_windows_slim")
if win.empty:
    win = load_precomputed("observing_windows")
print(f"load_windows:        {time.time()-start:.2f}s"
      f" — {len(win)} rows")

start = time.time()
atm = load_precomputed("atmospheric")
print(f"load_atmospheric:    {time.time()-start:.2f}s"
      f" — {len(atm)} rows")

start = time.time()
peak = load_precomputed("peak_times")
print(f"load_peak_times:     {time.time()-start:.2f}s"
      f" — {len(peak)} rows")

start = time.time()
eff = load_precomputed("efficiency_optical")
print(f"load_efficiency:     {time.time()-start:.2f}s"
      f" — {len(eff)} rows")

start = time.time()
from atmospheric import get_full_atmospheric_analysis
results = []
for _, row in df.head(50).iterrows():
    atm_live = get_full_atmospheric_analysis({
        "temperature_c":    row["temperature_c"],
        "wind_speed_ms":    row["wind_speed_ms"],
        "humidity_pct":     row["humidity_pct"],
        "altitude_m":       row["altitude_m"],
        "surface_pressure": row.get("surface_pressure"),
        "jet_stream_ms":    row.get("jet_stream_ms"),
        "latitude":         row["latitude"]
    })
    results.append(atm_live)
print(f"atmospheric live     {time.time()-start:.2f}s"
      f" — 50 observatories")

start = time.time()
from object_visibility import OBJECTS
print(f"load OBJECTS:        {time.time()-start:.2f}s"
      f" — {len(OBJECTS)} objects")

start = time.time()
from sky_chart import BRIGHT_STARS, PLANETS
print(f"load sky_chart:      {time.time()-start:.2f}s")

print("\nDone!")