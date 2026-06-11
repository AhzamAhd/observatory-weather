import requests
import pandas as pd
from datetime import datetime, timedelta

def fetch_forecast(lat, lon, days=7):
    """
    Fetch 7-day hourly weather forecast from Open-Meteo.
    Returns a DataFrame with daily summary scores.
    """
    url    = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "hourly": [
            "cloudcover",
            "relativehumidity_2m",
            "windspeed_10m",
            "temperature_2m",
            "precipitation_probability",
            "precipitation"
        ],
        "wind_speed_unit": "ms",
        "forecast_days":   days,
        "timezone":        "UTC"
    }

    try:
        response = requests.get(
            url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        hourly = data.get("hourly", {})
        times  = hourly.get("time", [])

        rows = []
        for i, time_str in enumerate(times):
            cloud  = hourly["cloudcover"][i]
            humid  = hourly["relativehumidity_2m"][i]
            wind   = hourly["windspeed_10m"][i]
            temp   = hourly["temperature_2m"][i]
            precip_prob = hourly.get(
                "precipitation_probability",
                [0]*len(times))[i]
            precip = hourly.get(
                "precipitation",
                [0]*len(times))[i]

            # Calculate observation score
            score = max(0, min(100,
                100
                - (cloud * 0.50)
                - (max(0, humid - 85) * 2.0)
                - (max(0, wind - 15) * 2.0)
            ))

            if score >= 80:   condition = "Excellent"
            elif score >= 60: condition = "Good"
            elif score >= 40: condition = "Marginal"
            else:             condition = "Poor"

            dt = datetime.fromisoformat(time_str)
            rows.append({
                "datetime":       dt,
                "date":           dt.strftime("%Y-%m-%d"),
                "hour":           dt.hour,
                "day_name":       dt.strftime("%A"),
                "date_display":   dt.strftime("%d %b"),
                "cloud_cover":    cloud,
                "humidity":       humid,
                "wind_speed":     wind,
                "temperature":    temp,
                "precip_prob":    precip_prob,
                "precip_mm":      precip,
                "score":          round(score, 1),
                "condition":      condition
            })

        df = pd.DataFrame(rows)
        return df

    except Exception as e:
        print(f"  [ERROR] Forecast fetch failed: {e}")
        return pd.DataFrame()

def _period_stats(grp):
    if grp.empty:
        return {"score": None, "cloud": None, "humidity": None,
                "wind": None, "temp": None, "precip_prob": None, "precip_mm": None}
    return {
        "score":      round(grp["score"].mean(), 0),
        "cloud":      round(grp["cloud_cover"].mean(), 0),
        "humidity":   round(grp["humidity"].mean(), 0),
        "wind":       round(grp["wind_speed"].mean(), 0),
        "temp":       round(grp["temperature"].mean(), 1),
        "precip_prob":round(grp["precip_prob"].max(), 0),
        "precip_mm":  round(grp["precip_mm"].sum(), 1),
    }

def get_daily_summary(forecast_df):
    if forecast_df.empty:
        return pd.DataFrame()

    daily = []
    for date, group in forecast_df.groupby("date"):
        am    = group[group["hour"].between(6, 11)]
        pm    = group[group["hour"].between(12, 17)]
        night = group[(group["hour"] >= 18) | (group["hour"] <= 5)]

        night_score = round(night["score"].mean(), 1) if not night.empty else round(group["score"].mean(), 1)
        best_hour   = group.loc[group["score"].idxmax(), "hour"]

        if night_score >= 80:   condition = "Excellent"
        elif night_score >= 60: condition = "Good"
        elif night_score >= 40: condition = "Marginal"
        else:                   condition = "Poor"

        daily.append({
            "date":         date,
            "day_name":     group.iloc[0]["day_name"],
            "date_display": group.iloc[0]["date_display"],
            "night_score":  night_score,
            "condition":    condition,
            "best_hour":    f"{best_hour:02d}:00 UTC",
            "min_temp":     round(group["temperature"].min(), 1),
            "max_temp":     round(group["temperature"].max(), 1),
            "avg_cloud":    round(group["cloud_cover"].mean(), 1),
            "avg_humidity": round(group["humidity"].mean(), 1),
            "avg_wind":     round(group["wind_speed"].mean(), 1),
            "precip_prob":  round(group["precip_prob"].max(), 1),
            "precip_mm":    round(group["precip_mm"].sum(), 1),
            "am":           _period_stats(am),
            "pm":           _period_stats(pm),
            "night":        _period_stats(night),
            "hourly_scores": group[["hour","score","condition","cloud_cover","humidity","wind_speed"]].to_dict("records"),
        })

    return pd.DataFrame(daily)


if __name__ == "__main__":
    print("\n Testing 7-day forecast...\n")
    # Mauna Kea
    df = fetch_forecast(19.8207, -155.4681)
    if not df.empty:
        daily = get_daily_summary(df)
        print(f"  {'Date':<12} {'Day':<12} "
              f"{'Night Score':<14} {'Condition':<12} "
              f"{'Cloud':<8} {'Best Hour'}")
        print("  " + "─" * 70)
        for _, row in daily.iterrows():
            print(
                f"  {row['date']:<12} "
                f"{row['day_name']:<12} "
                f"{row['night_score']:<14} "
                f"{row['condition']:<12} "
                f"{row['avg_cloud']}%{'':<4} "
                f"{row['best_hour']}"
            )