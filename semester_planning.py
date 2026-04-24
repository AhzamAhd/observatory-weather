import sqlite3
import pandas as pd
import calendar
from datetime import datetime, timedelta
import ephem
import math

def get_moon_phase_for_date(date):
    moon      = ephem.Moon(date.strftime("%Y/%m/%d"))
    phase_pct = moon.phase
    if phase_pct < 10:   name = "New"
    elif phase_pct < 35: name = "Crescent"
    elif phase_pct < 60: name = "Quarter"
    elif phase_pct < 85: name = "Gibbous"
    else:                name = "Full"
    return round(phase_pct, 1), name

def get_dark_hours_for_date(lat, lon, date):
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

def get_historical_scores(observatory_name, days=90):
    conn   = sqlite3.connect(
        "data/silver/observatory_weather.db")
    cutoff = (datetime.utcnow() - timedelta(days=days)
              ).strftime("%Y-%m-%d")
    df     = pd.read_sql("""
        SELECT
            w.fetch_date,
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
        WHERE o.name = ?
        AND w.fetch_date >= ?
        ORDER BY w.fetch_date
    """, conn, params=[observatory_name, cutoff])
    conn.close()
    return df

def get_observatory_location(observatory_name):
    conn = sqlite3.connect(
        "data/silver/observatory_weather.db")
    row  = pd.read_sql("""
        SELECT latitude, longitude, altitude_m, country
        FROM observatories WHERE name = ?
    """, conn, params=[observatory_name])
    conn.close()
    if row.empty:
        return None
    return row.iloc[0]

def build_calendar_data(observatory_name,
                         year=None, month_start=1,
                         months=6):
    if year is None:
        year = datetime.utcnow().year

    loc = get_observatory_location(observatory_name)
    if loc is None:
        return {}

    hist = get_historical_scores(observatory_name, days=365)
    hist_dict = {}
    if not hist.empty:
        for _, row in hist.iterrows():
            hist_dict[row["fetch_date"]] = row["daily_score"]

    calendar_data = {}

    for m in range(months):
        month = ((month_start - 1 + m) % 12) + 1
        yr    = year + ((month_start - 1 + m) // 12)

        _, days_in_month = calendar.monthrange(yr, month)
        month_key = f"{yr}-{month:02d}"
        calendar_data[month_key] = {
            "year":        yr,
            "month":       month,
            "month_name":  calendar.month_name[month],
            "days":        []
        }

        for day in range(1, days_in_month + 1):
            date     = datetime(yr, month, day)
            date_str = date.strftime("%Y-%m-%d")

            moon_pct, moon_name = get_moon_phase_for_date(date)
            dark_hours = get_dark_hours_for_date(
                loc["latitude"], loc["longitude"], date)

            # Use historical score if available
            # else estimate from moon and season
            if date_str in hist_dict:
                score        = hist_dict[date_str]
                is_actual    = True
            else:
                # Estimate: penalise full moon, reward dark hours
                moon_penalty = (moon_pct / 100) * 20
                dark_bonus   = min(20, dark_hours * 2)
                score        = max(
                    0, min(100, 70 - moon_penalty + dark_bonus))
                is_actual    = False

            # Moon penalty on score
            moon_adj_score = max(
                0, score - (moon_pct / 100) * 15)

            if moon_adj_score >= 80:   quality = "Excellent"
            elif moon_adj_score >= 60: quality = "Good"
            elif moon_adj_score >= 40: quality = "Marginal"
            else:                      quality = "Poor"

            calendar_data[month_key]["days"].append({
                "date":           date_str,
                "day":            day,
                "weekday":        date.weekday(),
                "score":          score,
                "moon_adj_score": round(moon_adj_score, 1),
                "quality":        quality,
                "moon_pct":       moon_pct,
                "moon_name":      moon_name,
                "dark_hours":     dark_hours,
                "is_actual":      is_actual
            })

        # Monthly summary
        days_list   = calendar_data[month_key]["days"]
        scores      = [d["moon_adj_score"] for d in days_list]
        excellent   = sum(
            1 for d in days_list if d["quality"] == "Excellent")
        good        = sum(
            1 for d in days_list if d["quality"] == "Good")
        poor        = sum(
            1 for d in days_list if d["quality"] == "Poor")
        new_moon_days = sum(
            1 for d in days_list if d["moon_pct"] < 10)

        calendar_data[month_key]["summary"] = {
            "avg_score":      round(
                sum(scores) / len(scores), 1),
            "excellent_days": excellent,
            "good_days":      good,
            "poor_days":      poor,
            "new_moon_days":  new_moon_days,
            "best_day":       max(
                days_list,
                key=lambda x: x["moon_adj_score"])["date"],
        }

    return calendar_data

def get_best_months(observatory_name, year=None, months=12):
    if year is None:
        year = datetime.utcnow().year

    data = build_calendar_data(
        observatory_name, year, month_start=1, months=months)

    summary = []
    for month_key, month_data in data.items():
        s = month_data["summary"]
        summary.append({
            "month":          month_data["month_name"],
            "month_num":      month_data["month"],
            "year":           month_data["year"],
            "avg_score":      s["avg_score"],
            "excellent_days": s["excellent_days"],
            "good_days":      s["good_days"],
            "poor_days":      s["poor_days"],
            "new_moon_days":  s["new_moon_days"],
            "best_day":       s["best_day"],
        })

    return pd.DataFrame(summary).sort_values(
        "excellent_days", ascending=False)


if __name__ == "__main__":
    conn  = sqlite3.connect(
        "data/silver/observatory_weather.db")
    name  = pd.read_sql(
        "SELECT name FROM observatories LIMIT 1",
        conn)["name"].iloc[0]
    conn.close()

    print(f"\n Building semester calendar for {name}...\n")
    best = get_best_months(name)
    print(f"  {'Month':<15} {'Avg':>6} "
          f"{'Excellent':>10} {'Good':>6} {'Poor':>6}")
    print("  " + "─" * 50)
    for _, row in best.iterrows():
        print(
            f"  {row['month']:<15} "
            f"{row['avg_score']:>6} "
            f"{row['excellent_days']:>10} "
            f"{row['good_days']:>6} "
            f"{row['poor_days']:>6}"
        )
    print(f"\n  Best month: {best.iloc[0]['month']}")
    print(
        f"  Excellent days: "
        f"{best.iloc[0]['excellent_days']}\n"
    )