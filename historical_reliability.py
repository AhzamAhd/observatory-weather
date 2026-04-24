import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def get_historical_data(days=30):
    """
    Fetch all weather readings from the past N days.
    """
    conn     = sqlite3.connect("data/silver/observatory_weather.db")
    cutoff   = (datetime.utcnow() - timedelta(days=days)
                ).strftime("%Y-%m-%d")

    df = pd.read_sql(f"""
        SELECT
            o.name       AS observatory,
            o.country,
            o.altitude_m,
            o.latitude,
            o.longitude,
            w.fetch_date,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS daily_score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        WHERE w.fetch_date >= '{cutoff}'
        ORDER BY o.name, w.fetch_date
    """, conn)
    conn.close()
    return df

def calculate_reliability_scores(days=30):
    """
    Calculate reliability metrics for each observatory
    based on historical data.
    """
    df = get_historical_data(days)

    if df.empty:
        return pd.DataFrame()

    results = []

    for observatory, group in df.groupby("observatory"):
        total_readings  = len(group)
        avg_score       = group["daily_score"].mean()
        median_score    = group["daily_score"].median()
        min_score       = group["daily_score"].min()
        max_score       = group["daily_score"].max()
        std_score       = group["daily_score"].std()

        # Consistency — lower std = more consistent
        consistency     = max(0, 100 - (std_score * 2))

        # Percentage of nights above threshold
        excellent_nights = len(
            group[group["daily_score"] >= 80])
        good_nights      = len(
            group[group["daily_score"] >= 60])
        poor_nights      = len(
            group[group["daily_score"] < 40])

        pct_excellent   = round(
            excellent_nights / total_readings * 100, 1)
        pct_good        = round(
            good_nights / total_readings * 100, 1)
        pct_poor        = round(
            poor_nights / total_readings * 100, 1)

        # Reliability grade
        # Based on average score + consistency + % excellent
        reliability_score = round(
            avg_score * 0.50 +
            consistency * 0.25 +
            pct_excellent * 0.25
        , 1)

        # Letter grade
        if reliability_score >= 85:   grade = "A+"
        elif reliability_score >= 80: grade = "A"
        elif reliability_score >= 75: grade = "A-"
        elif reliability_score >= 70: grade = "B+"
        elif reliability_score >= 65: grade = "B"
        elif reliability_score >= 60: grade = "B-"
        elif reliability_score >= 55: grade = "C+"
        elif reliability_score >= 50: grade = "C"
        elif reliability_score >= 45: grade = "C-"
        else:                         grade = "D"

        # Trend — is it getting better or worse?
        if total_readings >= 3:
            first_half = group.head(
                total_readings // 2)["daily_score"].mean()
            second_half = group.tail(
                total_readings // 2)["daily_score"].mean()
            trend_val   = second_half - first_half
            if trend_val > 5:     trend = "Improving ↑"
            elif trend_val < -5:  trend = "Declining ↓"
            else:                 trend = "Stable →"
        else:
            trend     = "Insufficient data"
            trend_val = 0

        # Best and worst day
        best_day  = group.loc[
            group["daily_score"].idxmax(), "fetch_date"]
        worst_day = group.loc[
            group["daily_score"].idxmin(), "fetch_date"]

        row = group.iloc[0]
        results.append({
            "observatory":       observatory,
            "country":           row["country"],
            "altitude_m":        row["altitude_m"],
            "latitude":          row["latitude"],
            "longitude":         row["longitude"],
            "days_of_data":      total_readings,
            "avg_score":         round(avg_score, 1),
            "median_score":      round(median_score, 1),
            "min_score":         round(min_score, 1),
            "max_score":         round(max_score, 1),
            "consistency":       round(consistency, 1),
            "reliability_score": reliability_score,
            "grade":             grade,
            "pct_excellent":     pct_excellent,
            "pct_good":          pct_good,
            "pct_poor":          pct_poor,
            "excellent_nights":  excellent_nights,
            "good_nights":       good_nights,
            "poor_nights":       poor_nights,
            "trend":             trend,
            "trend_val":         round(trend_val, 1),
            "best_day":          best_day,
            "worst_day":         worst_day,
            "daily_scores":      group[[
                "fetch_date", "daily_score"]
            ].to_dict("records")
        })

    return pd.DataFrame(results).sort_values(
        "reliability_score", ascending=False
    )

def get_grade_color(grade):
    if grade in ["A+", "A"]:  return "#1D9E75"
    elif grade == "A-":        return "#5DCAA5"
    elif grade in ["B+", "B"]: return "#378ADD"
    elif grade == "B-":        return "#85B7EB"
    elif grade in ["C+", "C"]: return "#EF9F27"
    elif grade == "C-":        return "#E8782A"
    else:                      return "#E24B4A"

def get_trend_emoji(trend):
    if "Improving" in trend:          return "📈"
    elif "Declining" in trend:        return "📉"
    elif "Stable" in trend:           return "➡️"
    else:                             return "❓"

if __name__ == "__main__":
    print("\n Calculating historical reliability scores...\n")
    df = calculate_reliability_scores(days=30)

    if df.empty:
        print("  No historical data yet.")
        print("  Run the pipeline daily for a few days "
              "to build history.\n")
    else:
        print(f"  Analysed {len(df)} observatories "
              f"over up to 30 days\n")
        print(f"  {'Observatory':<40} {'Grade':<6} "
              f"{'Reliability':<12} {'Avg Score':<12} "
              f"{'% Excellent':<12} {'Trend'}")
        print("  " + "─" * 90)
        for _, row in df.iterrows():
            print(
                f"  {row['observatory'][:38]:<40} "
                f"{row['grade']:<6} "
                f"{row['reliability_score']:<12} "
                f"{row['avg_score']:<12} "
                f"{row['pct_excellent']:<12} "
                f"{row['trend']}"
            )
        print(f"\n  Best site: {df.iloc[0]['observatory']}")
        print(f"  Grade    : {df.iloc[0]['grade']}")
        print(
            f"  Reliability: "
            f"{df.iloc[0]['reliability_score']}/100\n"
        )