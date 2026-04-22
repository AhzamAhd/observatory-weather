import streamlit as st
import sqlite3
import pandas as pd
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from streamlit_folium import st_folium
from datetime import datetime
from observing_window import get_all_windows
from object_visibility import (get_best_observatories_for_object,
                                calculate_visibility, OBJECTS,
                                get_ephem_object)
from peak_time import get_all_peak_times, calculate_hourly_scores
from atmospheric import get_full_atmospheric_analysis

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
            w.surface_pressure,
            w.jet_stream_ms,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS observation_score,
            CASE
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 80 THEN 'Excellent'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
                ) >= 60 THEN 'Good'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
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
    f"Last updated: "
    f"{df['fetch_datetime'].iloc[0] if not df.empty else 'No data'} "
    f"· {len(df)} observatories monitored "
    f"· {len(OBJECTS)} astronomical objects"
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 Live Weather Map",
    "🌙 Observing Windows",
    "🔭 Object Visibility",
    "⏰ Peak Observing Time",
    "🌫️ Atmospheric Analysis",
    "🔬 Observatory Detail"
])

# ═══════════════════════════════════════════════════════
# TAB 1 — Live Weather Map
# ═══════════════════════════════════════════════════════
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Observatories", len(df))
    c2.metric("Excellent Tonight",
              len(df[df["condition"] == "Excellent"]))
    c3.metric("Average Score",
              f"{round(df['observation_score'].mean(), 1)} / 100")
    c4.metric("Best Site Tonight",
              df.iloc[0]["observatory"].replace(
                  " Observatory", "").replace(" Telescope", ""))

    st.markdown("---")
    st.subheader("World map — live observation quality")

    m = folium.Map(location=[20, 0], zoom_start=2,
                   tiles="CartoDB positron")
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
            tooltip=f"{row['observatory']} — "
                    f"{row['observation_score']}/100"
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
            st.markdown(
                f"{emoji} **{row['observatory']}** "
                f"— {row['country']}")
            st.progress(
                int(row["observation_score"]) / 100,
                text=f"{row['observation_score']}/100 · "
                     f"Cloud {row['cloud_cover_pct']}% · "
                     f"Humidity {row['humidity_pct']}% · "
                     f"Wind {row['wind_speed_ms']} m/s"
            )
    with col_right:
        st.dataframe(
            df[["observatory", "observation_score",
                "condition"]].rename(columns={
                "observatory":       "Observatory",
                "observation_score": "Score",
                "condition":         "Condition"
            }),
            hide_index=True,
            height=700
        )

# ═══════════════════════════════════════════════════════
# TAB 2 — Observing Windows
# ═══════════════════════════════════════════════════════
with tab2:
    st.subheader("🌙 Tonight's Observing Windows")
    st.caption(
        "Scores adjusted for moon phase and position. "
        "Dark hours calculated using astronomical twilight (-18°)."
    )

    if not win.empty:
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Moon Phase",        win.iloc[0]["moon_phase"])
        w2.metric("Moon Illumination",
                  f"{win.iloc[0]['moon_phase_pct']}%")
        w3.metric("Best Site Tonight",
                  win.iloc[0]["observatory"].replace(
                      " Observatory", ""))
        w4.metric("Best Score (moon-adjusted)",
                  f"{win.iloc[0]['final_score']} / 100")

        st.markdown("---")
        st.subheader("Top 10 sites for tonight")
        for _, row in win.head(10).iterrows():
            emoji = condition_emoji(row["quality"])
            with st.expander(
                f"{emoji} {row['observatory']} — "
                f"{row['final_score']}/100 [{row['quality']}] · "
                f"{row['dark_start']} → {row['dark_end']} "
                f"({row['dark_hours']}h dark)"
            ):
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Weather Score",
                          f"{row['weather_score']}/100")
                d2.metric("Moon Penalty",
                          f"-{row['moon_penalty']}")
                d3.metric("Final Score",
                          f"{row['final_score']}/100")
                d4.metric("Dark Hours",
                          f"{row['dark_hours']}h")
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
        st.download_button(
            label="Download tonight's window table as CSV",
            data=display_df.to_csv(index=False),
            file_name=f"observing_windows_"
                      f"{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
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
            ["All", "Planets", "Dwarf Planets & Asteroids",
             "Galaxies", "Nebulae", "Star Clusters",
             "Famous Stars", "Special Objects",
             "Full Messier Catalogue", "NGC Objects"]
        )

    type_map = {
        "All":                       None,
        "Planets":                   "planet",
        "Dwarf Planets & Asteroids": ["dwarf_planet", "asteroid"],
        "Galaxies":                  "galaxy",
        "Nebulae":                   "nebula",
        "Star Clusters":             "cluster",
        "Famous Stars":              "star",
        "Special Objects":           "special",
        "Full Messier Catalogue":    "messier",
        "NGC Objects":               "ngc"
    }

    selected_type = type_map[obj_type]
    filtered_objects = {
        k: v for k, v in OBJECTS.items()
        if selected_type is None
        or (isinstance(selected_type, list)
            and v["type"] in selected_type)
        or (selected_type == "messier"
            and k.startswith("M") and "—" in k)
        or (selected_type == "ngc"
            and k.startswith("NGC"))
        or (isinstance(selected_type, str)
            and selected_type not in ["messier", "ngc"]
            and v["type"] == selected_type)
    }

    with col_select:
        selected_object = st.selectbox(
            "Select target object",
            list(filtered_objects.keys())
        )

    st.markdown("---")

    if selected_object:
        with st.spinner(
            f"Calculating visibility for {selected_object}..."
        ):
            best_obs = get_best_observatories_for_object(
                selected_object, df)

        if best_obs.empty:
            st.warning(
                f"{selected_object} is currently below the horizon "
                f"at all monitored observatories."
            )
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Observatories with view", len(best_obs))
            m2.metric("Best observatory",
                      best_obs.iloc[0]["observatory"].replace(
                          " Observatory", "").replace(
                          " Telescope", ""))
            m3.metric("Best altitude",
                      f"{best_obs.iloc[0]['altitude_deg']}°")
            m4.metric("Combined score",
                      f"{best_obs.iloc[0]['combined_score']} / 100")

            st.markdown("---")
            sample_vis = calculate_visibility(
                df.iloc[0]["latitude"],
                df.iloc[0]["longitude"],
                selected_object
            )
            obj_type_label = filtered_objects[
                selected_object]["type"].replace("_", " ").title()
            st.info(
                f"**{selected_object}** is a {obj_type_label}. "
                f"Currently visible from **{len(best_obs)}** of "
                f"{len(df)} monitored observatories. "
                f"Minimum altitude required: "
                f"{sample_vis['min_altitude']}° above horizon."
            )

            st.subheader(
                f"Best sites to observe {selected_object} tonight")
            for _, row in best_obs.head(10).iterrows():
                qual  = row["visibility_quality"]
                emoji = {"Excellent": "🟢", "Good": "🔵",
                         "Marginal": "🟡"}.get(qual, "⚪")
                with st.expander(
                    f"{emoji} {row['observatory']} — "
                    f"Combined {row['combined_score']}/100 · "
                    f"Altitude {row['altitude_deg']}° "
                    f"{row['direction']} · {qual}"
                ):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Altitude",
                              f"{row['altitude_deg']}°")
                    c2.metric("Direction",    row["direction"])
                    c3.metric("Weather Score",
                              f"{row['weather_score']}/100")
                    c4.metric("Hours Visible",
                              f"{row['hours_visible']}h")
                    c5.metric("Combined Score",
                              f"{row['combined_score']}/100")
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
            st.download_button(
                label=f"Download visibility table for "
                      f"{selected_object}",
                data=display.to_csv(index=False),
                file_name=f"visibility_"
                          f"{selected_object.replace(' ', '_')}_"
                          f"{datetime.utcnow().strftime('%Y-%m-%d')}"
                          f".csv",
                mime="text/csv"
            )

# ═══════════════════════════════════════════════════════
# TAB 4 — Peak Observing Time
# ═══════════════════════════════════════════════════════
with tab4:
    st.subheader("⏰ Peak Observing Time Calculator")
    st.caption(
        "Find the best hour to observe tonight at each observatory. "
        "Toggle on a target object to factor in its altitude "
        "alongside weather, darkness, and moon position."
    )

    use_object           = st.toggle(
        "Factor in a specific target object", value=False)
    selected_peak_object = None

    if use_object:
        pk_col1, pk_col2 = st.columns([1, 2])
        with pk_col1:
            pk_type = st.selectbox(
                "Object type",
                ["All", "Planets", "Galaxies", "Nebulae",
                 "Star Clusters", "Famous Stars",
                 "Full Messier Catalogue", "NGC Objects"],
                key="peak_type"
            )
        pk_type_map = {
            "All":                    None,
            "Planets":                "planet",
            "Galaxies":               "galaxy",
            "Nebulae":                "nebula",
            "Star Clusters":          "cluster",
            "Famous Stars":           "star",
            "Full Messier Catalogue": "messier",
            "NGC Objects":            "ngc"
        }
        pk_selected_type = pk_type_map[pk_type]
        pk_filtered = {
            k: v for k, v in OBJECTS.items()
            if pk_selected_type is None
            or (pk_selected_type == "messier"
                and k.startswith("M") and "—" in k)
            or (pk_selected_type == "ngc"
                and k.startswith("NGC"))
            or (isinstance(pk_selected_type, str)
                and pk_selected_type not in ["messier", "ngc"]
                and v["type"] == pk_selected_type)
        }
        with pk_col2:
            selected_peak_object = st.selectbox(
                "Select target object",
                list(pk_filtered.keys()),
                key="peak_object"
            )

    with st.spinner(
        "Calculating peak times across all observatories..."
    ):
        peak = get_all_peak_times(
            object_name=selected_peak_object)

    if selected_peak_object:
        st.success(
            f"Peak times calculated with "
            f"**{selected_peak_object}** altitude factored in."
        )

    if not peak.empty:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Best Observatory",
                  peak.iloc[0]["observatory"].replace(
                      " Observatory", "").replace(
                      " Telescope", ""))
        p2.metric("Peak Hour",    peak.iloc[0]["peak_hour"])
        p3.metric("Peak Score",
                  f"{peak.iloc[0]['peak_score']} / 100")
        p4.metric("Good Hours Tonight",
                  f"{peak.iloc[0]['total_good_hours']}h")

        st.markdown("---")

        selected_obs = st.selectbox(
            "Select observatory to see hourly breakdown",
            peak["observatory"].tolist(),
            key="peak_selector"
        )

        selected_row = peak[
            peak["observatory"] == selected_obs].iloc[0]

        st.markdown(
            f"**{selected_obs}** — "
            f"Peak at {selected_row['peak_hour']} · "
            f"Best window: {selected_row['window_start']} → "
            f"{selected_row['window_end']} · "
            f"{selected_row['total_good_hours']} good hours"
        )

        if selected_peak_object and selected_row.get("peak_obj_alt"):
            st.info(
                f"**{selected_peak_object}** reaches "
                f"**{selected_row['peak_obj_alt']}°** altitude "
                f"at peak observing time."
            )

        st.markdown("---")

        # Hourly chart
        fig, ax  = plt.subplots(figsize=(14, 5))
        hours    = [h["hour"]
                    for h in selected_row["hourly_data"]]
        scores   = [h["combined_score"]
                    for h in selected_row["hourly_data"]]
        obj_alts = [h.get("object_altitude")
                    for h in selected_row["hourly_data"]]

        colors = []
        for s in scores:
            if s >= 80:   colors.append("#1D9E75")
            elif s >= 60: colors.append("#378ADD")
            elif s >= 40: colors.append("#EF9F27")
            elif s > 0:   colors.append("#E24B4A")
            else:         colors.append("#444441")

        ax.bar(range(24), scores, color=colors, width=0.8)

        # Object altitude overlay
        if selected_peak_object and any(
            a is not None for a in obj_alts
        ):
            scaled = [
                (a / 90 * 100) if a is not None and a > 0 else 0
                for a in obj_alts
            ]
            ax.plot(range(24), scaled, color="white",
                    linewidth=1.5, linestyle="--",
                    alpha=0.7, label="Object altitude (scaled)")
            ax.legend(loc="upper right", fontsize=8,
                      facecolor="#0E1117", labelcolor="white")

        # Peak marker
        peak_idx = scores.index(max(scores))
        ax.bar(peak_idx, scores[peak_idx],
               color="#1D9E75", width=0.8,
               edgecolor="white", linewidth=2)
        ax.annotate(
            f"Peak\n{hours[peak_idx]}\n"
            f"{scores[peak_idx]:.0f}/100",
            xy=(peak_idx, scores[peak_idx]),
            xytext=(peak_idx, scores[peak_idx] + 8),
            ha="center", fontsize=9,
            color="white", fontweight="bold"
        )

        ax.set_xticks(range(24))
        ax.set_xticklabels(
            [f"{h:02d}:00" for h in range(24)],
            rotation=45, fontsize=8
        )
        ax.set_ylim(0, 115)
        ax.set_ylabel("Combined Observing Score", fontsize=10)
        ax.set_title(
            f"Hourly Observing Score — {selected_obs}"
            + (f" — {selected_peak_object}"
               if selected_peak_object else "")
            + f" — {datetime.utcnow().strftime('%Y-%m-%d')} UTC",
            fontsize=11, fontweight="bold"
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

        legend_items = [
            mpatches.Patch(color="#1D9E75",
                           label="Excellent (80+)"),
            mpatches.Patch(color="#378ADD",
                           label="Good (60-79)"),
            mpatches.Patch(color="#EF9F27",
                           label="Marginal (40-59)"),
            mpatches.Patch(color="#E24B4A",
                           label="Poor (<40)"),
            mpatches.Patch(color="#444441",
                           label="Daytime")
        ]
        ax.legend(handles=legend_items, loc="upper left",
                  fontsize=8, facecolor="#0E1117",
                  labelcolor="white")

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=150,
                    facecolor="#0E1117",
                    bbox_inches="tight")
        buf.seek(0)
        st.image(buf, use_container_width=True)
        plt.close()

        st.markdown("---")
        st.subheader("Hourly breakdown table")
        hourly = pd.DataFrame(selected_row["hourly_data"])
        cols   = ["hour", "sun_altitude", "moon_altitude",
                  "darkness_score", "moon_score",
                  "weather_score", "combined_score", "is_dark"]
        rename = {
            "hour":           "Hour (UTC)",
            "sun_altitude":   "Sun Alt (°)",
            "moon_altitude":  "Moon Alt (°)",
            "darkness_score": "Darkness",
            "moon_score":     "Moon Score",
            "weather_score":  "Weather",
            "combined_score": "Combined",
            "is_dark":        "Is Dark"
        }
        if selected_peak_object:
            cols.insert(4, "object_altitude")
            rename["object_altitude"] = "Object Alt (°)"
        st.dataframe(
            hourly[cols].rename(columns=rename),
            hide_index=True, height=400
        )

        st.markdown("---")
        st.subheader(
            "Top 10 observatories by peak score tonight")
        st.dataframe(
            peak.head(10)[[
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
            }),
            hide_index=True
        )

        st.download_button(
            label="Download peak times for all observatories",
            data=peak[[
                "observatory", "country", "peak_hour",
                "peak_score", "window_start", "window_end",
                "total_good_hours", "weather_score"
            ]].to_csv(index=False),
            file_name=f"peak_times_"
                      f"{datetime.utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )

# ═══════════════════════════════════════════════════════
# TAB 5 — Atmospheric Analysis
# ═══════════════════════════════════════════════════════
with tab5:
    st.subheader("🌫️ Atmospheric Analysis")
    st.caption(
        "Seeing index, Precipitable Water Vapor (PWV), and "
        "Jet Stream impact for every observatory. "
        "Essential for professional telescope scheduling."
    )

    # Calculate atmospheric data for all observatories
    atm_results = []
    for _, row in df.iterrows():
        record = {
            "temperature_c":    row["temperature_c"],
            "wind_speed_ms":    row["wind_speed_ms"],
            "humidity_pct":     row["humidity_pct"],
            "altitude_m":       row["altitude_m"],
            "surface_pressure": row.get("surface_pressure"),
            "jet_stream_ms":    row.get("jet_stream_ms"),
            "latitude":         row["latitude"]
        }
        atm = get_full_atmospheric_analysis(record)
        atm_results.append({
            "observatory":    row["observatory"],
            "country":        row["country"],
            "altitude_m":     row["altitude_m"],
            "weather_score":  row["observation_score"],
            **atm
        })

    atm_df = pd.DataFrame(atm_results).sort_values(
        "seeing_arcsec", ascending=True
    )

    # Summary metrics
    a1, a2, a3, a4 = st.columns(4)
    best_seeing = atm_df.iloc[0]
    best_pwv    = atm_df.sort_values(
        "pwv_mm", ascending=True).iloc[0]
    low_jet     = atm_df[
        atm_df["jet_impact"] == "Negligible"]

    a1.metric("Best Seeing",
              f"{best_seeing['seeing_arcsec']}\"",
              best_seeing["observatory"].replace(
                  " Observatory", ""))
    a2.metric("Lowest PWV",
              f"{best_pwv['pwv_mm']} mm",
              best_pwv["observatory"].replace(
                  " Observatory", ""))
    a3.metric("Calm Jet Stream Sites", len(low_jet))
    a4.metric("Observatories Analysed", len(atm_df))

    st.markdown("---")

    # World map coloured by seeing
    st.subheader("World map — atmospheric seeing index")
    st.caption(
        "Circle colour shows estimated seeing in arcseconds. "
        "Green = exceptional, Red = poor."
    )

    m_atm = folium.Map(
        location=[20, 0], zoom_start=2,
        tiles="CartoDB positron"
    )

    for _, row in atm_df.iterrows():
        obs_row = df[
            df["observatory"] == row["observatory"]].iloc[0]
        color   = row["seeing_color"]

        popup_html = f"""
            <div style='font-family:sans-serif;width:220px'>
                <b>{row['observatory']}</b><br>
                {row['country']} · {row['altitude_m']}m<br>
                <hr style='margin:4px 0'>
                <b>Seeing:</b> {row['seeing_arcsec']}"
                [{row['seeing_quality']}]<br>
                <b>PWV:</b> {row['pwv_mm']} mm
                [{row['pwv_quality']}]<br>
                <b>Jet stream:</b> {row['jet_stream_ms']} m/s
                [{row['jet_impact']}]<br>
                <hr style='margin:4px 0'>
                Weather score: {row['weather_score']}/100
            </div>
        """
        folium.CircleMarker(
            location=[obs_row["latitude"],
                      obs_row["longitude"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=230),
            tooltip=f"{row['observatory']} — "
                    f"Seeing {row['seeing_arcsec']}\" "
                    f"[{row['seeing_quality']}]"
        ).add_to(m_atm)

    st_folium(m_atm, width=None, height=500)

    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
    sc1.markdown("🟢 **< 0.5\"** Exceptional")
    sc2.markdown("🟩 **< 1.0\"** Excellent")
    sc3.markdown("🔵 **< 1.5\"** Good")
    sc4.markdown("🟡 **< 2.5\"** Average")
    sc5.markdown("🔴 **< 3.5\"** Poor")
    sc6.markdown("🟥 **> 3.5\"** Very Poor")

    st.markdown("---")

    # Three sub-tabs for each metric
    seeing_tab, pwv_tab, jet_tab = st.tabs([
        "👁️ Seeing Index",
        "💧 Precipitable Water Vapor",
        "🌪️ Jet Stream"
    ])

    with seeing_tab:
        st.subheader("Atmospheric seeing rankings")
        st.caption(
            "Seeing measures atmospheric turbulence. "
            "Lower arcseconds = sharper images. "
            "Professional telescopes need < 1.5\" to operate "
            "at full resolution."
        )
        for _, row in atm_df.iterrows():
            bar_val = max(0, min(1,
                1 - (row["seeing_arcsec"] - 0.3) / 4.7))
            st.markdown(
                f"**{row['observatory']}** — "
                f"{row['seeing_arcsec']}\" "
                f"[{row['seeing_quality']}] · "
                f"{row['country']}"
            )
            st.progress(
                bar_val,
                text=f"Seeing {row['seeing_arcsec']}\" · "
                     f"Alt {row['altitude_m']}m · "
                     f"Wind {row.get('weather_score', 0)}/100 "
                     f"weather"
            )

    with pwv_tab:
        st.subheader("Precipitable Water Vapor rankings")
        st.caption(
            "PWV measures water vapour in the atmosphere. "
            "Critical for infrared and radio astronomy. "
            "< 2mm is excellent for IR work. "
            "Sites like ALMA require < 1mm."
        )
        pwv_sorted = atm_df.sort_values(
            "pwv_mm", ascending=True)
        for _, row in pwv_sorted.iterrows():
            bar_val = max(0, min(1,
                1 - (row["pwv_mm"] / 30)))
            st.markdown(
                f"**{row['observatory']}** — "
                f"{row['pwv_mm']} mm "
                f"[{row['pwv_quality']}] · "
                f"{row['country']}"
            )
            st.progress(
                bar_val,
                text=f"PWV {row['pwv_mm']} mm · "
                     f"Altitude {row['altitude_m']}m"
            )

    with jet_tab:
        st.subheader("Jet stream impact rankings")
        st.caption(
            "The jet stream at ~10km altitude causes the worst "
            "atmospheric seeing when directly overhead. "
            "Below 20 m/s is ideal. Above 60 m/s degrades "
            "image quality severely."
        )
        jet_sorted = atm_df.sort_values(
            "jet_stream_ms", ascending=True)
        for _, row in jet_sorted.iterrows():
            js  = row["jet_stream_ms"] or 0
            bar_val = max(0, min(1, 1 - (js / 100)))
            st.markdown(
                f"**{row['observatory']}** — "
                f"{js} m/s "
                f"[{row['jet_impact']}] · "
                f"{row['country']}"
            )
            st.progress(
                bar_val,
                text=f"Jet stream {js} m/s · "
                     f"Impact: {row['jet_impact']}"
            )

    st.markdown("---")

    # Full atmospheric table
    st.subheader("Complete atmospheric data table")
    atm_display = atm_df[[
        "observatory", "country", "altitude_m",
        "seeing_arcsec", "seeing_quality",
        "pwv_mm", "pwv_quality",
        "jet_stream_ms", "jet_impact",
        "weather_score"
    ]].rename(columns={
        "observatory":   "Observatory",
        "country":       "Country",
        "altitude_m":    "Altitude (m)",
        "seeing_arcsec": "Seeing (\")",
        "seeing_quality":"Seeing Quality",
        "pwv_mm":        "PWV (mm)",
        "pwv_quality":   "PWV Quality",
        "jet_stream_ms": "Jet Stream (m/s)",
        "jet_impact":    "Jet Impact",
        "weather_score": "Weather Score"
    })
    st.dataframe(atm_display, hide_index=True, height=600)

    st.download_button(
        label="Download atmospheric analysis as CSV",
        data=atm_display.to_csv(index=False),
        file_name=f"atmospheric_analysis_"
                  f"{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )
# ═══════════════════════════════════════════════════════
# TAB 5 — Observatory Detail
# ═══════════════════════════════════════════════════════
with tab6:
    st.subheader("🔬 Observatory detail view")
    selected = st.selectbox(
        "Select an observatory",
        df["observatory"].tolist()
    )
    row  = df[df["observatory"] == selected].iloc[0]
    wrow = win[win["observatory"] == selected]

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Weather Score",
              f"{row['observation_score']} / 100")
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
        f"**{row['observatory']}** is located in "
        f"{row['country']} at {row['altitude_m']}m altitude "
        f"(MPC code: {row['mpc_code']}). "
        f"Current weather condition: **{row['condition']}** "
        f"as of {row['fetch_datetime']}."
    )

st.markdown("---")
st.caption(
    "Data from Open-Meteo · "
    "Observatory list from Minor Planet Center (MPC) · "
    "Astronomical calculations via PyEphem · "
    f"{len(OBJECTS)} objects in catalogue · "
    "Pipeline runs daily at 06:00 UTC via GitHub Actions"
)