import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from observing_window import get_all_windows

st.set_page_config(
    page_title="Observatory Weather Tracker",
    page_icon="🔭",
    layout="wide"
)

@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect("data/silver/observatory_weather.db")
    df = pd.read_sql("""
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

@st.cache_data(ttl=300)
def load_windows():
    return get_all_windows()

def score_color(score):
    if score >= 80:   return "#1D9E75"
    elif score >= 60: return "#378ADD"
    elif score >= 40: return "#EF9F27"
    else:             return "#E24B4A"

def condition_emoji(condition):
    return {"Excellent": "🟢", "Good": "🔵",
            "Marginal": "🟡", "Poor": "🔴"}.get(condition, "⚪")

df  = load_data()
win = load_windows()

st.title("🔭 Global Observatory Weather Tracker")
st.caption(
    f"Last updated: {df['fetch_datetime'].iloc[0] if not df.empty else 'No data'} "
    f"· {len(df)} observatories monitored"
)

tab1, tab2, tab3 = st.tabs([
    "🌍 Live Weather Map",
    "🌙 Observing Windows",
    "🔬 Observatory Detail"
])

# ═══════════════════════════════════════════════════════
# TAB 1 — Live Weather Map
# ═══════════════════════════════════════════════════════
with tab1:

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Observatories", len(df))
    with c2:
        st.metric("Excellent Tonight", len(df[df["condition"] == "Excellent"]))
    with c3:
        st.metric("Average Score", f"{round(df['observation_score'].mean(), 1)} / 100")
    with c4:
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
                Score: <b>{row['observation_score']} / 100</b>
                [{row['condition']}]<br>
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

# ═══════════════════════════════════════════════════════
# TAB 2 — Observing Windows
# ═══════════════════════════════════════════════════════
with tab2:

    st.subheader("🌙 Tonight's Observing Windows")
    st.caption("Scores adjusted for moon phase and position. "
               "Dark hours calculated using astronomical twilight (-18°).")

    if not win.empty:

        moon_phase = win.iloc[0]["moon_phase"]
        moon_pct   = win.iloc[0]["moon_phase_pct"]
        best_site  = win.iloc[0]["observatory"]
        best_window = f"{win.iloc[0]['dark_start']} → {win.iloc[0]['dark_end']}"
        best_score  = win.iloc[0]["final_score"]

        w1, w2, w3, w4 = st.columns(4)
        with w1:
            st.metric("Moon Phase", moon_phase)
        with w2:
            st.metric("Moon Illumination", f"{moon_pct}%")
        with w3:
            st.metric("Best Site Tonight", best_site.replace(" Observatory", ""))
        with w4:
            st.metric("Best Score (moon-adjusted)", f"{best_score} / 100")

        st.markdown("---")

        # Top 10 sites
        st.subheader("Top 10 sites for tonight")
        top10 = win.head(10)
        for _, row in top10.iterrows():
            emoji = condition_emoji(row["quality"])
            with st.expander(
                f"{emoji} {row['observatory']} — "
                f"{row['final_score']}/100 [{row['quality']}] · "
                f"{row['dark_start']} → {row['dark_end']} "
                f"({row['dark_hours']}h dark)"
            ):
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Weather Score",  f"{row['weather_score']}/100")
                d2.metric("Moon Penalty",   f"-{row['moon_penalty']}")
                d3.metric("Final Score",    f"{row['final_score']}/100")
                d4.metric("Dark Hours",     f"{row['dark_hours']}h")

                m1, m2, m3 = st.columns(3)
                m1.metric("Moon Phase",     row["moon_phase"])
                m2.metric("Moon Rise",      row["moon_rise"])
                m3.metric("Moon Set",       row["moon_set"])

        st.markdown("---")

        # Full table
        st.subheader("All observatories — full window table")
        display_df = win[[
            "observatory", "country", "dark_start", "dark_end",
            "dark_hours", "moon_phase", "moon_phase_pct",
            "weather_score", "moon_penalty", "final_score", "quality"
        ]].rename(columns={
            "observatory":    "Observatory",
            "country":        "Country",
            "dark_start":     "Dark Start",
            "dark_end":       "Dark End",
            "dark_hours":     "Dark Hours",
            "moon_phase":     "Moon Phase",
            "moon_phase_pct": "Moon %",
            "weather_score":  "Weather Score",
            "moon_penalty":   "Moon Penalty",
            "final_score":    "Final Score",
            "quality":        "Quality"
        })
        st.dataframe(display_df, hide_index=True, height=600)

        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Download tonight's window table as CSV",
            data=csv,
            file_name=f"observing_windows_{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

# ═══════════════════════════════════════════════════════
# TAB 3 — Observatory Detail
# ═══════════════════════════════════════════════════════
with tab3:

    st.subheader("🔬 Observatory detail view")

    selected = st.selectbox(
        "Select an observatory",
        df["observatory"].tolist()
    )

    row  = df[df["observatory"] == selected].iloc[0]
    wrow = win[win["observatory"] == selected]

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Weather Score",  f"{row['observation_score']} / 100")
    d2.metric("Cloud Cover",    f"{row['cloud_cover_pct']}%")
    d3.metric("Humidity",       f"{row['humidity_pct']}%")
    d4.metric("Wind Speed",     f"{row['wind_speed_ms']} m/s")
    d5.metric("Temperature",    f"{row['temperature_c']}°C")

    if not wrow.empty:
        w = wrow.iloc[0]
        st.markdown("---")
        st.markdown("**Tonight's observing window**")
        w1, w2, w3, w4, w5 = st.columns(5)
        w1.metric("Dark Start",    w["dark_start"])
        w2.metric("Dark End",      w["dark_end"])
        w3.metric("Dark Hours",    f"{w['dark_hours']}h")
        w4.metric("Moon Phase",    w["moon_phase"])
        w5.metric("Final Score",   f"{w['final_score']} / 100")

    st.markdown("---")
    st.info(
        f"**{row['observatory']}** is located in {row['country']} "
        f"at {row['altitude_m']}m altitude (MPC code: {row['mpc_code']}). "
        f"Current weather condition: **{row['condition']}** "
        f"as of {row['fetch_datetime']}."
    )

st.markdown("---")
st.caption(
    "Data from Open-Meteo · Observatory list from Minor Planet Center (MPC) · "
    "Astronomical calculations via PyEphem · "
    "Pipeline runs daily at 06:00 UTC via GitHub Actions"
)