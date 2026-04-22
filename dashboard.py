import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(
    page_title="Observatory Weather Tracker",
    page_icon="🔭",
    layout="wide"
)

@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect("data/silver/observatory_weather.db")
    df   = pd.read_sql("""
        SELECT
            o.name         AS observatory,
            o.country,
            o.latitude,
            o.longitude,
            o.altitude_m,
            o.mpc_code,
            w.fetch_date,
            w.fetch_time,
            w.fetch_datetime,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            w.precipitation_mm,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS observation_score,
            CASE
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 80 THEN 'Excellent'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 60 THEN 'Good'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85 THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15 THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 40 THEN 'Marginal'
                ELSE 'Poor'
            END AS condition
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        ORDER BY observation_score DESC
    """, conn)
    conn.close()
    return df

def score_color(score):
    if score >= 80:   return "#1D9E75"
    elif score >= 60: return "#378ADD"
    elif score >= 40: return "#EF9F27"
    else:             return "#E24B4A"

def condition_emoji(condition):
    return {"Excellent": "🟢", "Good": "🔵",
            "Marginal": "🟡", "Poor": "🔴"}.get(condition, "⚪")

df = load_data()

st.title("🔭 Global Observatory Weather Tracker")
st.caption(f"Last updated: {df['fetch_datetime'].iloc[0] if not df.empty else 'No data yet'} · {len(df)} observatories monitored")

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Observatories", len(df))
with col2:
    st.metric("Excellent Tonight", len(df[df["condition"] == "Excellent"]))
with col3:
    st.metric("Average Score", f"{round(df['observation_score'].mean(), 1)} / 100")
with col4:
    best = df.iloc[0]["observatory"].replace(" Observatory", "").replace(" Telescope", "")
    st.metric("Best Site Tonight", best)

st.markdown("---")

st.subheader("World map — live observation quality")

m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")

for _, row in df.iterrows():
    color = score_color(row["observation_score"])
    popup_html = f"""
        <div style='font-family:sans-serif;width:210px'>
            <b>{row['observatory']}</b><br>
            {row['country']} · Alt: {row['altitude_m']}m
            · MPC: {row['mpc_code']}<br>
            <hr style='margin:4px 0'>
            Score: <b>{row['observation_score']} / 100</b> [{row['condition']}]<br>
            Cloud: {row['cloud_cover_pct']}% |
            Humidity: {row['humidity_pct']}%<br>
            Wind: {row['wind_speed_ms']} m/s |
            Temp: {row['temperature_c']}°C<br>
            <small>Fetched: {row['fetch_time']}</small>
        </div>
    """
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        popup=folium.Popup(popup_html, max_width=220),
        tooltip=f"{row['observatory']} — {row['observation_score']}/100"
    ).add_to(m)

st_folium(m, width=None, height=500)

lc1, lc2, lc3, lc4 = st.columns(4)
lc1.markdown("🟢 **Excellent** — 80 to 100")
lc2.markdown("🔵 **Good** — 60 to 79")
lc3.markdown("🟡 **Marginal** — 40 to 59")
lc4.markdown("🔴 **Poor** — 0 to 39")

st.markdown("---")

st.subheader("Observation quality rankings")

col_left, col_right = st.columns([2, 1])

with col_left:
    for _, row in df.iterrows():
        emoji = condition_emoji(row["condition"])
        st.markdown(f"{emoji} **{row['observatory']}** — {row['country']}")
        st.progress(
            int(row["observation_score"]) / 100,
            text=f"{row['observation_score']}/100 · "
                 f"Cloud {row['cloud_cover_pct']}% · "
                 f"Humidity {row['humidity_pct']}% · "
                 f"Wind {row['wind_speed_ms']} m/s"
        )

with col_right:
    st.dataframe(
        df[["observatory", "observation_score", "condition"]].rename(columns={
            "observatory": "Observatory",
            "observation_score": "Score",
            "condition": "Condition"
        }),
        hide_index=True,
        height=700
    )

st.markdown("---")

st.subheader("Observatory detail view")
selected = st.selectbox("Select an observatory", df["observatory"].tolist())
row = df[df["observatory"] == selected].iloc[0]

d1, d2, d3, d4, d5 = st.columns(5)
d1.metric("Score",       f"{row['observation_score']} / 100")
d2.metric("Cloud Cover", f"{row['cloud_cover_pct']}%")
d3.metric("Humidity",    f"{row['humidity_pct']}%")
d4.metric("Wind Speed",  f"{row['wind_speed_ms']} m/s")
d5.metric("Temperature", f"{row['temperature_c']}°C")

st.info(
    f"**{row['observatory']}** is located in {row['country']} "
    f"at {row['altitude_m']}m altitude (MPC code: {row['mpc_code']}). "
    f"Current condition: **{row['condition']}** as of {row['fetch_datetime']}."
)

st.markdown("---")
st.caption("Data from Open-Meteo · Observatory list from Minor Planet Center (MPC) · "
           "Pipeline runs daily at 06:00 UTC via GitHub Actions")