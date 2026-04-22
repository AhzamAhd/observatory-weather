import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
from observing_window import get_all_windows
from object_visibility import get_best_observatories_for_object, calculate_visibility, OBJECTS
from peak_time import get_all_peak_times, calculate_hourly_scores

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

@st.cache_data(ttl=300)
def load_peak_times():
    return get_all_peak_times()

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
peak = load_peak_times()

st.title("🔭 Global Observatory Weather Tracker")
st.caption(
    f"Last updated: {df['fetch_datetime'].iloc[0] if not df.empty else 'No data'} "
    f"· {len(df)} observatories monitored"
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌍 Live Weather Map",
    "🌙 Observing Windows",
    "🔭 Object Visibility",
    "⏰ Peak Observing Time",
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
        moon_phase  = win.iloc[0]["moon_phase"]
        moon_pct    = win.iloc[0]["moon_phase_pct"]
        best_site   = win.iloc[0]["observatory"]
        best_score  = win.iloc[0]["final_score"]

        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Moon Phase", moon_phase)
        w2.metric("Moon Illumination", f"{moon_pct}%")
        w3.metric("Best Site Tonight",
                  best_site.replace(" Observatory", ""))
        w4.metric("Best Score (moon-adjusted)", f"{best_score} / 100")

        st.markdown("---")
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
                m1.metric("Moon Phase", row["moon_phase"])
                m2.metric("Moon Rise",  row["moon_rise"])
                m3.metric("Moon Set",   row["moon_set"])

        st.markdown("---")
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
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Download tonight's window table as CSV",
            data=csv,
            file_name=f"observing_windows_{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

# ═══════════════════════════════════════════════════════
# TAB 3 — Object Visibility
# ═══════════════════════════════════════════════════════
with tab3:
    st.subheader("🔭 Object Visibility Calculator")
    st.caption(
        "Find which observatories worldwide have the best view "
        "of your target object right now. Combines weather score "
        "with object altitude for a combined ranking."
    )

    col_filter, col_select = st.columns([1, 2])
    with col_filter:
        obj_type = st.selectbox(
            "Filter by type",
            ["All", "Planets", "Deep Sky Objects", "Stars"]
        )
    type_map = {
        "All":              None,
        "Planets":          "planet",
        "Deep Sky Objects": "deep_sky",
        "Stars":            "star"
    }
    selected_type    = type_map[obj_type]
    filtered_objects = {
        k: v for k, v in OBJECTS.items()
        if selected_type is None or v["type"] == selected_type
    }
    with col_select:
        selected_object = st.selectbox(
            "Select target object",
            list(filtered_objects.keys())
        )

    st.markdown("---")

    if selected_object:
        with st.spinner(f"Calculating visibility for {selected_object}..."):
            best_obs = get_best_observatories_for_object(selected_object, df)

        if best_obs.empty:
            st.warning(f"{selected_object} is currently below the horizon "
                       f"at all monitored observatories.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Observatories with view", len(best_obs))
            m2.metric("Best observatory",
                      best_obs.iloc[0]["observatory"].replace(
                          " Observatory", "").replace(" Telescope", ""))
            m3.metric("Best altitude",
                      f"{best_obs.iloc[0]['altitude_deg']}°")
            m4.metric("Combined score",
                      f"{best_obs.iloc[0]['combined_score']} / 100")

            st.markdown("---")

            sample_vis     = calculate_visibility(
                df.iloc[0]["latitude"],
                df.iloc[0]["longitude"],
                selected_object
            )
            obj_type_label = filtered_objects[selected_object]["type"].replace(
                "_", " ").title()
            st.info(
                f"**{selected_object}** is a {obj_type_label}. "
                f"Currently visible from **{len(best_obs)}** of "
                f"{len(df)} monitored observatories. "
                f"Minimum altitude required: "
                f"{sample_vis['min_altitude']}° above horizon."
            )

            st.subheader(f"Best sites to observe {selected_object} tonight")
            top10 = best_obs.head(10)
            for _, row in top10.iterrows():
                qual  = row["visibility_quality"]
                emoji = {"Excellent": "🟢", "Good": "🔵",
                         "Marginal": "🟡"}.get(qual, "⚪")
                with st.expander(
                    f"{emoji} {row['observatory']} — "
                    f"Combined {row['combined_score']}/100 · "
                    f"Altitude {row['altitude_deg']}° {row['direction']} · "
                    f"{qual}"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Altitude",       f"{row['altitude_deg']}°")
                    c2.metric("Direction",      row["direction"])
                    c3.metric("Weather Score",  f"{row['weather_score']}/100")
                    c4.metric("Hours Visible",  f"{row['hours_visible']}h")
                    c5.metric("Combined Score", f"{row['combined_score']}/100")
                    st.caption(
                        f"Rises: {row['rise_time']} · "
                        f"Sets: {row['set_time']} · "
                        f"Located in {row['country']}"
                    )

            st.markdown("---")
            st.subheader("All observatories with visibility")
            display = best_obs[[
                "observatory", "country", "altitude_deg",
                "direction", "hours_visible", "rise_time",
                "set_time", "weather_score", "combined_score",
                "visibility_quality"
            ]].rename(columns={
                "observatory":        "Observatory",
                "country":            "Country",
                "altitude_deg":       "Altitude (°)",
                "direction":          "Direction",
                "hours_visible":      "Hours Visible",
                "rise_time":          "Rises",
                "set_time":           "Sets",
                "weather_score":      "Weather Score",
                "combined_score":     "Combined Score",
                "visibility_quality": "Quality"
            })
            st.dataframe(display, hide_index=True, height=500)
            csv = display.to_csv(index=False)
            st.download_button(
                label=f"Download visibility table for {selected_object}",
                data=csv,
                file_name=f"visibility_{selected_object.replace(' ', '_')}"
                          f"_{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
                mime="text/csv"
            )

# ═══════════════════════════════════════════════════════
# TAB 4 — Observatory Detail
# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# TAB 4 — Peak Observing Time
# ═══════════════════════════════════════════════════════
with tab4:
    st.subheader("⏰ Peak Observing Time Calculator")
    st.caption(
        "Find the single best hour to observe tonight at each "
        "observatory. Combines weather, darkness, and moon position "
        "into an hourly score across all 24 hours."
    )

    if not peak.empty:

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Best Observatory",
                  peak.iloc[0]["observatory"].replace(
                      " Observatory", "").replace(" Telescope", ""))
        p2.metric("Peak Hour",        peak.iloc[0]["peak_hour"])
        p3.metric("Peak Score",       f"{peak.iloc[0]['peak_score']} / 100")
        p4.metric("Good Hours Tonight", f"{peak.iloc[0]['total_good_hours']}h")

        st.markdown("---")

        # Observatory selector
        selected_obs = st.selectbox(
            "Select observatory to see hourly breakdown",
            peak["observatory"].tolist(),
            key="peak_selector"
        )

        selected_row  = peak[peak["observatory"] == selected_obs].iloc[0]
        hourly        = pd.DataFrame(selected_row["hourly_data"])

        st.markdown(f"**{selected_obs}** — "
                    f"Peak at {selected_row['peak_hour']} · "
                    f"Best window: {selected_row['window_start']} → "
                    f"{selected_row['window_end']} · "
                    f"{selected_row['total_good_hours']} good hours")

        st.markdown("---")

        # Hourly chart
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import io

        fig, ax = plt.subplots(figsize=(14, 5))
        hours   = [h["hour"] for h in selected_row["hourly_data"]]
        scores  = [h["combined_score"] for h in selected_row["hourly_data"]]
        colors  = []
        for s in scores:
            if s >= 80:   colors.append("#1D9E75")
            elif s >= 60: colors.append("#378ADD")
            elif s >= 40: colors.append("#EF9F27")
            elif s > 0:   colors.append("#E24B4A")
            else:         colors.append("#444441")

        bars = ax.bar(range(24), scores, color=colors, width=0.8)

        # Mark peak hour
        peak_idx = scores.index(max(scores))
        ax.bar(peak_idx, scores[peak_idx],
               color="#1D9E75", width=0.8,
               edgecolor="white", linewidth=2)
        ax.annotate(
            f"Peak\n{hours[peak_idx]}\n{scores[peak_idx]:.0f}/100",
            xy=(peak_idx, scores[peak_idx]),
            xytext=(peak_idx, scores[peak_idx] + 8),
            ha="center", fontsize=9, color="white",
            fontweight="bold"
        )

        ax.set_xticks(range(24))
        ax.set_xticklabels(
            [f"{h:02d}:00" for h in range(24)],
            rotation=45, fontsize=8
        )
        ax.set_ylim(0, 115)
        ax.set_ylabel("Combined Observing Score", fontsize=10)
        ax.set_title(
            f"Hourly Observing Score — {selected_obs} — "
            f"{datetime.utcnow().strftime('%Y-%m-%d')} UTC",
            fontsize=12, fontweight="bold"
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#0E1117")
        fig.patch.set_facecolor("#0E1117")
        ax.tick_params(colors="white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        ax.spines["left"].set_color("#444441")
        ax.spines["bottom"].set_color("#444441")

        legend = [
            mpatches.Patch(color="#1D9E75", label="Excellent (80+)"),
            mpatches.Patch(color="#378ADD", label="Good (60-79)"),
            mpatches.Patch(color="#EF9F27", label="Marginal (40-59)"),
            mpatches.Patch(color="#E24B4A", label="Poor (<40)"),
            mpatches.Patch(color="#444441", label="Daytime")
        ]
        ax.legend(handles=legend, loc="upper left",
                  fontsize=8, facecolor="#0E1117",
                  labelcolor="white")

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=150,
                    facecolor="#0E1117", bbox_inches="tight")
        buf.seek(0)
        st.image(buf, use_container_width=True)
        plt.close()

        st.markdown("---")

        # Hourly data table
        st.subheader("Hourly breakdown table")
        hourly_display = hourly[[
            "hour", "sun_altitude", "moon_altitude",
            "darkness_score", "moon_score",
            "weather_score", "combined_score", "is_dark"
        ]].rename(columns={
            "hour":           "Hour (UTC)",
            "sun_altitude":   "Sun Alt (°)",
            "moon_altitude":  "Moon Alt (°)",
            "darkness_score": "Darkness Score",
            "moon_score":     "Moon Score",
            "weather_score":  "Weather Score",
            "combined_score": "Combined Score",
            "is_dark":        "Is Dark"
        })
        st.dataframe(hourly_display, hide_index=True, height=400)

        st.markdown("---")

        # Top 10 peak times across all observatories
        st.subheader("Top 10 observatories by peak score tonight")
        top10_peak = peak.head(10)[[
            "observatory", "country", "peak_hour",
            "peak_score", "window_start", "window_end",
            "total_good_hours", "weather_score"
        ]].rename(columns={
            "observatory":      "Observatory",
            "country":          "Country",
            "peak_hour":        "Peak Hour",
            "peak_score":       "Peak Score",
            "window_start":     "Window Start",
            "window_end":       "Window End",
            "total_good_hours": "Good Hours",
            "weather_score":    "Weather Score"
        })
        st.dataframe(top10_peak, hide_index=True)

        # Download
        csv = peak[[
            "observatory", "country", "peak_hour",
            "peak_score", "window_start", "window_end",
            "total_good_hours", "weather_score"
        ]].to_csv(index=False)
        st.download_button(
            label="Download peak times for all observatories",
            data=csv,
            file_name=f"peak_times_{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

with tab5:
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
        w1.metric("Dark Start",  w["dark_start"])
        w2.metric("Dark End",    w["dark_end"])
        w3.metric("Dark Hours",  f"{w['dark_hours']}h")
        w4.metric("Moon Phase",  w["moon_phase"])
        w5.metric("Final Score", f"{w['final_score']} / 100")

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