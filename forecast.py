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

def get_daily_summary(forecast_df):
    """
    Summarise hourly forecast into daily scores.
    """
    if forecast_df.empty:
        return pd.DataFrame()

    daily = []
    for date, group in forecast_df.groupby("date"):
        # Night hours only (18:00 - 06:00)
        night = group[
            (group["hour"] >= 18) |
            (group["hour"] <= 6)
        ]
        all_hours = group

        avg_score      = round(
            all_hours["score"].mean(), 1)
        night_score    = round(
            night["score"].mean(), 1) if not night.empty else avg_score
        best_hour_idx  = all_hours["score"].idxmax()
        best_hour      = all_hours.loc[
            best_hour_idx, "hour"]
        best_score     = all_hours.loc[
            best_hour_idx, "score"]

        avg_cloud  = round(all_hours["cloud_cover"].mean(), 1)
        avg_humid  = round(all_hours["humidity"].mean(), 1)
        avg_wind   = round(all_hours["wind_speed"].mean(), 1)
        min_temp   = round(all_hours["temperature"].min(), 1)
        max_temp   = round(all_hours["temperature"].max(), 1)
        precip_prob = round(
            all_hours["precip_prob"].max(), 1)

        if night_score >= 80:   condition = "Excellent"
        elif night_score >= 60: condition = "Good"
        elif night_score >= 40: condition = "Marginal"
        else:                   condition = "Poor"

        daily.append({
            "date":          date,
            "day_name":      group.iloc[0]["day_name"],
            "date_display":  group.iloc[0]["date_display"],
            "avg_score":     avg_score,
            "night_score":   night_score,
            "condition":     condition,
            "best_hour":     f"{best_hour:02d}:00 UTC",
            "best_score":    round(best_score, 1),
            "avg_cloud":     avg_cloud,
            "avg_humidity":  avg_humid,
            "avg_wind":      avg_wind,
            "min_temp":      min_temp,
            "max_temp":      max_temp,
            "precip_prob":   precip_prob,
            "hourly_scores": group[[
                "hour", "score", "condition",
                "cloud_cover", "humidity",
                "wind_speed"
            ]].to_dict("records")
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