import pandas as pd
from datetime import datetime

def generate_kml(df):
    """
    Generate KML file for all observatories.
    Colour coded by observation score.
    Opens in Google Earth showing all 1275 sites.
    """

    def score_to_kml_color(score):
        # KML colors are AABBGGRR format
        if score >= 80:   return "ff75be1d"  # Green
        elif score >= 60: return "ffdd8a37"  # Blue
        elif score >= 40: return "ff27afef"  # Orange
        else:             return "ff4a4be2"  # Red

    def score_to_icon(score):
        if score >= 80:   return "grn-circle"
        elif score >= 60: return "blu-circle"
        elif score >= 40: return "ylw-circle"
        else:             return "red-circle"

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'  <name>Global Observatory Weather Tracker</name>',
        f'  <description>Live observation quality for {len(df)} observatories worldwide. Generated {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</description>',
        '',
        '  <!-- Styles -->',
    ]

    # Add styles for each condition
    for condition, color, icon in [
        ("Excellent", "ff75be1d", "http://maps.google.com/mapfiles/kml/paddle/grn-circle.png"),
        ("Good",      "ffdd8a37", "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png"),
        ("Marginal",  "ff27afef", "http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png"),
        ("Poor",      "ff4a4be2", "http://maps.google.com/mapfiles/kml/paddle/red-circle.png"),
    ]:
        lines += [
            f'  <Style id="style_{condition}">',
            f'    <IconStyle>',
            f'      <color>{color}</color>',
            f'      <scale>0.8</scale>',
            f'      <Icon><href>{icon}</href></Icon>',
            f'    </IconStyle>',
            f'    <LabelStyle><scale>0</scale></LabelStyle>',
            f'  </Style>',
        ]

    # Add folders by condition
    for condition in ["Excellent", "Good", "Marginal", "Poor"]:
        subset = df[df["condition"] == condition]
        if subset.empty:
            continue

        lines += [
            f'  <Folder>',
            f'    <name>{condition} — {len(subset)} sites</name>',
            f'    <visibility>1</visibility>',
        ]

        for _, row in subset.iterrows():
            score       = row["observation_score"]
            name        = row["observatory"].replace("&", "&amp;").replace("<", "&lt;")
            country     = row["country"].replace("&", "&amp;")
            lat         = row["latitude"]
            lon         = row["longitude"]
            alt         = row.get("altitude_m", 0) or 0
            cloud       = row.get("cloud_cover_pct", "N/A")
            humidity    = row.get("humidity_pct", "N/A")
            wind        = row.get("wind_speed_ms", "N/A")
            temp        = row.get("temperature_c", "N/A")
            fetch_time  = row.get("fetch_time", "N/A")

            description = (
                f"<![CDATA["
                f"<b>{name}</b><br/>"
                f"{country} · {alt}m altitude<br/>"
                f"<hr/>"
                f"<b>Score: {score}/100 [{condition}]</b><br/>"
                f"Cloud: {cloud}% · Humidity: {humidity}%<br/>"
                f"Wind: {wind} m/s · Temp: {temp}°C<br/>"
                f"<small>Updated: {fetch_time}</small>"
                f"]]>"
            )

            lines += [
                f'    <Placemark>',
                f'      <name>{name}</name>',
                f'      <description>{description}</description>',
                f'      <styleUrl>#style_{condition}</styleUrl>',
                f'      <Point>',
                f'        <coordinates>{lon},{lat},{alt}</coordinates>',
                f'      </Point>',
                f'    </Placemark>',
            ]

        lines.append(f'  </Folder>')

    lines += ['</Document>', '</kml>']
    return "\n".join(lines)


def generate_csv_for_maps(df):
    """
    Generate CSV that can be imported into
    Google My Maps directly.
    """
    export = df[[
        "observatory", "country", "latitude",
        "longitude", "altitude_m", "observation_score",
        "condition", "cloud_cover_pct", "humidity_pct",
        "wind_speed_ms", "temperature_c"
    ]].rename(columns={
        "observatory":       "Name",
        "country":           "Country",
        "latitude":          "Latitude",
        "longitude":         "Longitude",
        "altitude_m":        "Altitude (m)",
        "observation_score": "Score",
        "condition":         "Condition",
        "cloud_cover_pct":   "Cloud %",
        "humidity_pct":      "Humidity %",
        "wind_speed_ms":     "Wind m/s",
        "temperature_c":     "Temp C"
    })
    return export.to_csv(index=False)


if __name__ == "__main__":
    from db import query_df
    df = query_df("""
        SELECT
            o.name AS observatory, o.country,
            o.latitude, o.longitude, o.altitude_m,
            w.fetch_time,
            w.cloud_cover_pct, w.humidity_pct,
            w.wind_speed_ms, w.temperature_c,
            ROUND(GREATEST(0,
                100 - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct-85)*2 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
            )::numeric, 1) AS observation_score,
            CASE
                WHEN (100 - (w.cloud_cover_pct*0.50)
                    - (CASE WHEN w.humidity_pct>85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms>15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 80 THEN 'Excellent'
                WHEN (100 - (w.cloud_cover_pct*0.50)
                    - (CASE WHEN w.humidity_pct>85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms>15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 60 THEN 'Good'
                WHEN (100 - (w.cloud_cover_pct*0.50)
                    - (CASE WHEN w.humidity_pct>85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms>15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 40 THEN 'Marginal'
                ELSE 'Poor'
            END AS condition
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        WHERE w.fetch_date = (
            SELECT MAX(fetch_date) FROM weather_readings
        )
        ORDER BY observation_score DESC
    """)

    kml = generate_kml(df)
    csv = generate_csv_for_maps(df)

    with open("observatories.kml", "w", encoding="utf-8") as f:
        f.write(kml)
    with open("observatories_maps.csv", "w", encoding="utf-8") as f:
        f.write(csv)

    print(f"\n  Generated files:")
    print(f"  observatories.kml — open in Google Earth")
    print(f"  observatories_maps.csv — import to Google My Maps")
    print(f"  {len(df)} observatories exported\n")