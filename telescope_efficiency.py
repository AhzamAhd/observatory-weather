import sqlite3
import pandas as pd
import ephem
import math
from datetime import datetime, timedelta
from atmospheric import get_full_atmospheric_analysis

def get_dark_hours(lat, lon, date=None):
    if date is None:
        date = datetime.utcnow()

    obs          = ephem.Observer()
    obs.lat      = str(lat)
    obs.long     = str(lon)
    obs.date     = date.strftime("%Y/%m/%d 12:00:00")
    obs.pressure = 0
    sun          = ephem.Sun()

    try:
        obs.horizon = "-18"
        dusk        = obs.next_setting(
            sun, use_center=True).datetime()
        dawn        = obs.next_rising(
            sun, use_center=True).datetime()
        dark_hours  = (dawn - dusk).total_seconds() / 3600
        if dark_hours < 0:
            dark_hours += 24
        return round(dark_hours, 1)
    except Exception:
        return 0

def get_moon_dark_fraction(lat, lon, date=None):
    """
    Returns fraction of dark hours that are
    moon-free (0 to 1). 1 = no moon all night.
    """
    if date is None:
        date = datetime.utcnow()

    obs          = ephem.Observer()
    obs.lat      = str(lat)
    obs.long     = str(lon)
    obs.pressure = 0

    # Check each hour of the night
    moon_free_hours = 0
    total_dark      = 0

    for h in range(24):
        dt           = date.replace(
            hour=h, minute=0, second=0)
        obs.date     = dt.strftime("%Y/%m/%d %H:%M:%S")

        sun  = ephem.Sun()
        moon = ephem.Moon()
        sun.compute(obs)
        moon.compute(obs)

        sun_alt  = math.degrees(float(sun.alt))
        moon_alt = math.degrees(float(moon.alt))

        if sun_alt < -18:    # astronomical night
            total_dark += 1
            if moon_alt <= 0:  # moon below horizon
                moon_free_hours += 1

    if total_dark == 0:
        return 1.0
    return round(moon_free_hours / total_dark, 2)

def calculate_efficiency_score(
    weather_score,
    dark_hours,
    moon_free_fraction,
    seeing_arcsec,
    pwv_mm,
    jet_impact,
    altitude_m,
    telescope_type="optical"
):
    """
    Calculate telescope time efficiency score.

    This answers: how many truly usable hours
    will this telescope produce tonight?

    Components:
    - Weather quality (40%)
    - Dark hours available (25%)
    - Moon-free fraction (15%)
    - Atmospheric seeing (10%) — optical only
    - PWV (10%) — infrared/radio weighted higher
    """

    # ── Weather component (0–100) ─────────────────────
    weather_component = weather_score

    # ── Dark hours component (0–100) ──────────────────
    # 12 hours = perfect score, less = proportionally lower
    dark_component = min(100, (dark_hours / 12) * 100)

    # ── Moon component (0–100) ────────────────────────
    moon_component = moon_free_fraction * 100

    # ── Seeing component (0–100) ──────────────────────
    if seeing_arcsec is None:
        seeing_component = 50
    elif seeing_arcsec < 0.5:   seeing_component = 100
    elif seeing_arcsec < 1.0:   seeing_component = 85
    elif seeing_arcsec < 1.5:   seeing_component = 70
    elif seeing_arcsec < 2.5:   seeing_component = 50
    elif seeing_arcsec < 3.5:   seeing_component = 30
    else:                        seeing_component = 10

    # ── PWV component (0–100) ─────────────────────────
    if pwv_mm is None:
        pwv_component = 50
    elif pwv_mm < 1.0:   pwv_component = 100
    elif pwv_mm < 2.0:   pwv_component = 85
    elif pwv_mm < 5.0:   pwv_component = 65
    elif pwv_mm < 10.0:  pwv_component = 40
    else:                pwv_component = 15

    # ── Jet stream component (0–100) ──────────────────
    jet_scores = {
        "Negligible": 100,
        "Low":        80,
        "Moderate":   55,
        "High":       30,
        "Severe":     10,
        "Unknown":    50
    }
    jet_component = jet_scores.get(jet_impact, 50)

    # ── Altitude bonus ────────────────────────────────
    # Higher sites get a small bonus
    altitude_bonus = min(10, altitude_m / 1000)

    # ── Weights by telescope type ─────────────────────
    if telescope_type == "optical":
        weights = {
            "weather":  0.40,
            "dark":     0.25,
            "moon":     0.15,
            "seeing":   0.12,
            "pwv":      0.05,
            "jet":      0.03
        }
    elif telescope_type == "infrared":
        weights = {
            "weather":  0.30,
            "dark":     0.20,
            "moon":     0.10,
            "seeing":   0.08,
            "pwv":      0.25,
            "jet":      0.07
        }
    elif telescope_type == "radio":
        weights = {
            "weather":  0.20,
            "dark":     0.05,
            "moon":     0.05,
            "seeing":   0.05,
            "pwv":      0.45,
            "jet":      0.20
        }
    else:
        weights = {
            "weather":  0.40,
            "dark":     0.25,
            "moon":     0.15,
            "seeing":   0.10,
            "pwv":      0.05,
            "jet":      0.05
        }

    # ── Final score ───────────────────────────────────
    raw_score = (
        weather_component  * weights["weather"] +
        dark_component     * weights["dark"]    +
        moon_component     * weights["moon"]    +
        seeing_component   * weights["seeing"]  +
        pwv_component      * weights["pwv"]     +
        jet_component      * weights["jet"]     +
        altitude_bonus
    )

    final_score = round(min(100, max(0, raw_score)), 1)

    # ── Usable hours estimate ─────────────────────────
    usable_hours = round(
        dark_hours *
        (weather_score / 100) *
        moon_free_fraction, 1
    )

    # ── Grade ─────────────────────────────────────────
    if final_score >= 85:   grade = "A+"
    elif final_score >= 80: grade = "A"
    elif final_score >= 75: grade = "A-"
    elif final_score >= 70: grade = "B+"
    elif final_score >= 65: grade = "B"
    elif final_score >= 60: grade = "B-"
    elif final_score >= 50: grade = "C"
    else:                   grade = "D"

    return {
        "efficiency_score":   final_score,
        "grade":              grade,
        "usable_hours":       usable_hours,
        "dark_hours":         dark_hours,
        "moon_free_fraction": moon_free_fraction,
        "components": {
            "weather":  round(
                weather_component * weights["weather"], 1),
            "dark":     round(
                dark_component * weights["dark"], 1),
            "moon":     round(
                moon_component * weights["moon"], 1),
            "seeing":   round(
                seeing_component * weights["seeing"], 1),
            "pwv":      round(
                pwv_component * weights["pwv"], 1),
            "jet":      round(
                jet_component * weights["jet"], 1),
            "altitude_bonus": round(altitude_bonus, 1)
        }
    }

def get_all_efficiency_scores(telescope_type="optical"):
    """
    Calculate efficiency scores for all observatories.
    """
    conn = sqlite3.connect(
        "data/silver/observatory_weather.db")
    df   = pd.read_sql("""
        SELECT
            o.name       AS observatory,
            o.country,
            o.altitude_m,
            o.latitude,
            o.longitude,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            w.surface_pressure,
            w.jet_stream_ms,
            w.fetch_datetime,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct-85)*2 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
            ), 1) AS weather_score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        ORDER BY o.name
    """, conn)
    conn.close()

    results = []

    for _, row in df.iterrows():
        try:
            # Get atmospheric data
            atm = get_full_atmospheric_analysis({
                "temperature_c":    row["temperature_c"],
                "wind_speed_ms":    row["wind_speed_ms"],
                "humidity_pct":     row["humidity_pct"],
                "altitude_m":       row["altitude_m"],
                "surface_pressure": row.get(
                    "surface_pressure"),
                "jet_stream_ms":    row.get("jet_stream_ms"),
                "latitude":         row["latitude"]
            })

            # Get dark hours
            dark_hours = get_dark_hours(
                row["latitude"], row["longitude"])

            # Get moon-free fraction
            moon_free  = get_moon_dark_fraction(
                row["latitude"], row["longitude"])

            # Calculate efficiency
            eff = calculate_efficiency_score(
                weather_score     = row["weather_score"],
                dark_hours        = dark_hours,
                moon_free_fraction = moon_free,
                seeing_arcsec     = atm["seeing_arcsec"],
                pwv_mm            = atm["pwv_mm"],
                jet_impact        = atm["jet_impact"],
                altitude_m        = row["altitude_m"],
                telescope_type    = telescope_type
            )

            results.append({
                "observatory":      row["observatory"],
                "country":          row["country"],
                "altitude_m":       row["altitude_m"],
                "latitude":         row["latitude"],
                "longitude":        row["longitude"],
                "weather_score":    row["weather_score"],
                "efficiency_score": eff["efficiency_score"],
                "grade":            eff["grade"],
                "usable_hours":     eff["usable_hours"],
                "dark_hours":       eff["dark_hours"],
                "moon_free_pct":    round(
                    eff["moon_free_fraction"] * 100, 1),
                "seeing_arcsec":    atm["seeing_arcsec"],
                "pwv_mm":           atm["pwv_mm"],
                "jet_impact":       atm["jet_impact"],
                "components":       eff["components"],
                "fetch_datetime":   row["fetch_datetime"]
            })

        except Exception as e:
            print(f"  [SKIP] {row['observatory']} — {e}")
            continue

    return pd.DataFrame(results).sort_values(
        "efficiency_score", ascending=False
    )
def get_cross_type_comparison():
    """
    Calculate efficiency scores for all three
    telescope types and compare rankings side by side.
    """
    print("  Calculating optical scores...")
    optical   = get_all_efficiency_scores("optical")
    print("  Calculating infrared scores...")
    infrared  = get_all_efficiency_scores("infrared")
    print("  Calculating radio scores...")
    radio     = get_all_efficiency_scores("radio")

    if optical.empty:
        return pd.DataFrame()

    # Add rank columns
    optical["optical_rank"]    = range(1, len(optical) + 1)
    infrared["infrared_rank"]  = range(1, len(infrared) + 1)
    radio["radio_rank"]        = range(1, len(radio) + 1)

    # Merge all three
    merged = optical[[
        "observatory", "country", "altitude_m",
        "weather_score", "dark_hours",
        "moon_free_pct", "seeing_arcsec",
        "pwv_mm", "jet_impact",
        "efficiency_score", "grade",
        "usable_hours", "optical_rank",
        "latitude", "longitude"
    ]].copy()

    merged = merged.rename(columns={
        "efficiency_score": "optical_score",
        "grade":            "optical_grade",
        "usable_hours":     "optical_usable_hrs"
    })

    ir_cols = infrared[[
        "observatory",
        "efficiency_score", "grade",
        "usable_hours", "infrared_rank"
    ]].rename(columns={
        "efficiency_score": "infrared_score",
        "grade":            "infrared_grade",
        "usable_hours":     "infrared_usable_hrs"
    })

    radio_cols = radio[[
        "observatory",
        "efficiency_score", "grade",
        "usable_hours", "radio_rank"
    ]].rename(columns={
        "efficiency_score": "radio_score",
        "grade":            "radio_grade",
        "usable_hours":     "radio_usable_hrs"
    })

    result = merged.merge(
        ir_cols, on="observatory", how="left"
    ).merge(
        radio_cols, on="observatory", how="left"
    )

    # Best type for each observatory
    def best_type(row):
        scores = {
            "Optical":  row["optical_score"],
            "Infrared": row["infrared_score"],
            "Radio":    row["radio_score"]
        }
        return max(scores, key=scores.get)

    def rank_change(row):
        opt  = row["optical_rank"]
        ir   = row["infrared_rank"]
        rad  = row["radio_rank"]
        best = min(opt, ir, rad)
        worst = max(opt, ir, rad)
        return worst - best

    result["best_type"]    = result.apply(
        best_type, axis=1)
    result["rank_spread"]  = result.apply(
        rank_change, axis=1)

    return result.sort_values(
        "optical_score", ascending=False)

if __name__ == "__main__":
    print("\n Calculating telescope efficiency scores...\n")
    df = get_all_efficiency_scores("optical")

    if df.empty:
        print("  No data found.")
    else:
        print(
            f"  {'Observatory':<40} {'Grade':<6} "
            f"{'Efficiency':<12} {'Usable hrs':<12} "
            f"{'Dark hrs':<10} {'Weather'}"
        )
        print("  " + "─" * 85)
        for _, row in df.head(15).iterrows():
            print(
                f"  {row['observatory'][:38]:<40} "
                f"{row['grade']:<6} "
                f"{row['efficiency_score']:<12} "
                f"{row['usable_hours']:<12} "
                f"{row['dark_hours']:<10} "
                f"{row['weather_score']}"
            )
        print(
            f"\n  Best site: {df.iloc[0]['observatory']}")
        print(
            f"  Grade    : {df.iloc[0]['grade']}")
        print(
            f"  Usable hrs: "
            f"{df.iloc[0]['usable_hours']}h tonight\n"
        )