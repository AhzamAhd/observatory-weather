import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import os
os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"
from comet_tracker import (get_current_comets,
                            get_comet_visibility,
                            magnitude_to_visibility,
                            comet_type_info)

from reviews import (add_review, get_reviews,
                     get_observatory_stats,
                     get_top_rated_observatories,
                     get_recent_reviews,
                     get_rating_distribution,
                     stars, rating_color)
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
import streamlit as st
import math
import sqlite3
import pandas as pd
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from streamlit_folium import st_folium
from observing_window import get_all_windows
from object_visibility import (get_best_observatories_for_object,
                                calculate_visibility, OBJECTS,
                                get_ephem_object)
from peak_time import get_all_peak_times, calculate_hourly_scores
from atmospheric import get_full_atmospheric_analysis
from historical_reliability import (calculate_reliability_scores,
                                     get_grade_color,
                                     get_trend_emoji)
from site_comparison import compare_sites
from semester_planning import build_calendar_data, get_best_months
import calendar
from educational_mode import (get_all_concepts,
                               get_concepts_by_category)
from sheets_subscriptions import (add_subscription,
                                   remove_subscription,
                                   load_subscriptions)
from telescope_efficiency import get_all_efficiency_scores
from snr_calculator import (calculate_snr, get_snr_for_all_observatories,
                              TELESCOPE_SPECS, OBJECT_MAGNITUDES,
                              get_sky_brightness)
from sky_chart import compute_sky
from satellite_tracker import (get_all_passes,
                                get_iss_tle,
                                calculate_passes,
                                get_current_position,
                                magnitude_visibility,
                                magnitude_emoji)
from forecast import fetch_forecast, get_daily_summary

st.set_page_config(
    page_title="Observatory Weather Tracker",
    page_icon="🔭",
    layout="wide"
)

@st.cache_resource
def get_all_precomputed():
    from precompute import load_precomputed
    return {
        "windows":    load_precomputed(
            "observing_windows_slim"),
        "atmospheric": load_precomputed("atmospheric"),
        "peak_times":  load_precomputed("peak_times"),
        "efficiency":  load_precomputed(
            "efficiency_optical")
    }

_precomputed = get_all_precomputed()
@st.cache_data(ttl=3600)  # cache for 1 hour
def load_atmospheric():
    from atmospheric import get_full_atmospheric_analysis
    df      = load_data()
    results = []
    for _, row in df.iterrows():
        atm = get_full_atmospheric_analysis({
            "temperature_c":    row["temperature_c"],
            "wind_speed_ms":    row["wind_speed_ms"],
            "humidity_pct":     row["humidity_pct"],
            "altitude_m":       row["altitude_m"],
            "surface_pressure": row.get("surface_pressure"),
            "jet_stream_ms":    row.get("jet_stream_ms"),
            "latitude":         row["latitude"]
        })
        results.append({
            "observatory":  row["observatory"],
            "country":      row["country"],
            "altitude_m":   row["altitude_m"],
            "weather_score": row["observation_score"],
            **atm
        })
    return pd.DataFrame(results).sort_values(
        "seeing_arcsec", ascending=True)

@st.cache_data(ttl=3600)
def load_data():
    from db import query_df
    return query_df("""
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
            ROUND(GREATEST(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0
                   ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0
                   ELSE 0 END)
            )::numeric, 1) AS observation_score,
            CASE
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 80 THEN 'Excellent'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
                       THEN (w.wind_speed_ms-15)*2 ELSE 0 END)
                ) >= 60 THEN 'Good'
                WHEN (100 - (w.cloud_cover_pct * 0.50)
                    - (CASE WHEN w.humidity_pct > 85
                       THEN (w.humidity_pct-85)*2 ELSE 0 END)
                    - (CASE WHEN w.wind_speed_ms > 15
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
    conn.close()
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def load_windows():
    data = _precomputed.get(
        "windows", pd.DataFrame())
    if not data.empty:
        return data
    from precompute import load_precomputed
    data = load_precomputed("observing_windows_slim")
    if not data.empty:
        return data
    return load_precomputed("observing_windows")

@st.cache_data(ttl=3600, show_spinner=False)
def load_peak_times_cached(object_name=None):
    if object_name:
        from peak_time import get_all_peak_times
        return get_all_peak_times(object_name)
    data = _precomputed.get(
        "peak_times", pd.DataFrame())
    if not data.empty:
        return data
    from precompute import load_precomputed
    return load_precomputed("peak_times")

@st.cache_data(ttl=3600, show_spinner=False)
def load_atmospheric_cached():
    data = _precomputed.get(
        "atmospheric", pd.DataFrame())
    if not data.empty:
        return data
    from precompute import load_precomputed
    return load_precomputed("atmospheric")

@st.cache_data(ttl=3600, show_spinner=False)
def load_efficiency_cached(telescope_type="optical"):
    if telescope_type == "optical":
        data = _precomputed.get(
            "efficiency", pd.DataFrame())
        if not data.empty:
            return data
    from precompute import load_precomputed
    return load_precomputed(
        f"efficiency_{telescope_type}")

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
peak = load_peak_times_cached()

st.title("🔭 Global Observatory Weather Tracker")
st.caption(
    f"Last updated: "
    f"{df['fetch_datetime'].iloc[0] if not df.empty else 'No data'} "
    f"· {len(df)} observatories monitored "
    f"· {len(OBJECTS)} astronomical objects"
)

(tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8,
 tab9, tab10, tab11, tab12, tab13, tab14, tab15,
 tab16, tab17, tab18) = st.tabs([
    "🌍 Live Weather Map",
    "🌙 Observing Windows",
    "🔭 Object Visibility",
    "⏰ Peak Observing Time",
    "🌫️ Atmospheric Analysis",
    "📊 Historical Reliability",
    "⚖️ Site Comparison",
    "📅 Semester Planning",
    "🎓 Learn Astronomy",
    "🔔 Alert Subscriptions",
    "🏆 Telescope Efficiency",
    "📡 SNR Calculator",
    "🌌 Live Sky Chart",
    "📅 7-Day Forecast",
    "📷 All-Sky Cameras",
    "☄️ Comet Tracker",
    "🛸 Satellite Passes",
    "⭐ Observatory Reviews",
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

    st.markdown("---")
    st.subheader("📥 Export for Google Maps / Google Earth")
    st.caption(
        "Download your observatory data to view in "
        "Google Maps or Google Earth with live scores."
    )

    from export_kml import generate_kml, generate_csv_for_maps

    ex1, ex2 = st.columns(2)

    with ex1:
        kml_data = generate_kml(df)
        st.download_button(
            label="🌍 Download KML for Google Earth",
            data=kml_data,
            file_name=f"observatories_{utcnow().strftime('%Y-%m-%d')}.kml",
            mime="application/vnd.google-earth.kml+xml",
            help="Open this file in Google Earth to see all observatories with live scores"
        )
        st.caption(
            "Opens in Google Earth desktop or web. "
            "Shows all observatories colour-coded by "
            "observation quality."
        )

    with ex2:
        csv_data = generate_csv_for_maps(df)
        st.download_button(
            label="🗺️ Download CSV for Google My Maps",
            data=csv_data,
            file_name=f"observatories_maps_{utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            help="Import to maps.google.com/maps/d to create your own custom map"
        )
        st.caption(
            "Go to maps.google.com/maps/d → Create → Import. "
            "Creates a custom Google Map with all 1275 observatories."
        )

    st.info(
        "💡 **Google My Maps tip:** After importing the CSV, "
        "click 'Style by data column' → select 'Condition' "
        "to colour-code markers by Excellent/Good/Marginal/Poor."
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
                      f"{utcnow().strftime('%Y-%m-%d')}.csv",
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
            "Full Messier Catalogue", "NGC Objects",
            "Exoplanets"]
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
        "NGC Objects":               "ngc",
        "Exoplanets":                "exoplanet"
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

# Show extra info for exoplanets
            if filtered_objects.get(selected_object, {}).get(
                    "type") == "exoplanet":
                from exoplanets import get_exoplanet_info
                exo_info = get_exoplanet_info(selected_object)
                if exo_info:
                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("Distance",
                             f"{exo_info['distance_ly']} ly")
                    e2.metric("Planet Type",
                             exo_info["type"])
                    e3.metric("Discovery Year",
                             exo_info["discovery_year"])
                    e4.metric("Discovery Method",
                             exo_info["method"])
                    st.info(
                       f"**{exo_info['name']}** orbits "
                       f"**{exo_info['host']}** at "
                       f"{exo_info['distance_ly']} light years. "
                       f"Discovered in {exo_info['discovery_year']} "
                       f"using {exo_info['method']}. "
                       f"{exo_info['notes']}."
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
                          f"{utcnow().strftime('%Y-%m-%d')}"
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
            "NGC Objects":            "ngc",
            "Exoplanets":             "exoplanet"
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
                and pk_selected_type not in ["messier", "ngc", "exoplanet"]
                and v["type"] == pk_selected_type)
        }
        with pk_col2:
            selected_peak_object = st.selectbox(
                "Select target object",
                list(pk_filtered.keys()),
                key="peak_object"
            )

    with st.spinner(...):
        peak = load_peak_times_cached(
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
            + f" — {utcnow().strftime('%Y-%m-%d')} UTC",
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
        plt.savefig(buf, format="png", dpi=120,
                    facecolor="#0E1117",
                    bbox_inches="tight")
        buf.seek(0)
        img_data = buf.getvalue()
        buf.close()
        plt.close()
        st.image(img_data, width='stretch')

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
                      f"{utcnow().strftime('%Y-%m-%d')}"
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
    atm_df = load_atmospheric_cached()

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
        obs_match = df[df["observatory"] == row["observatory"]]
        if obs_match.empty:
            continue
        obs_row = obs_match.iloc[0]
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
                  f"{utcnow().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )
# ═══════════════════════════════════════════════════════
# TAB 6 — Historical Reliability
# ═══════════════════════════════════════════════════════
with tab6:
    st.subheader("📊 Historical Reliability Scoring")
    st.caption(
        "Reliability grades based on accumulated daily weather "
        "data. The longer the pipeline runs, the more accurate "
        "these scores become. Updated automatically every day."
    )

    days_option = st.selectbox(
        "Analysis window",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"Last {x} days"
    )

    with st.spinner(
        f"Calculating reliability scores over "
        f"last {days_option} days..."
    ):
        hist_df = calculate_reliability_scores(days=days_option)

    if hist_df.empty:
        st.warning(
            "Not enough historical data yet. "
            "The pipeline needs to run for at least 2 days "
            "to show trends. Check back tomorrow!"
        )
        st.info(
            "💡 Every day the pipeline runs at 06:00 UTC "
            "via GitHub Actions, adding another day of data. "
            "After 7 days you will see meaningful reliability "
            "scores. After 30 days the grades become very "
            "accurate."
        )
    else:
        # Summary metrics
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Observatories Ranked",  len(hist_df))
        h2.metric("Days of Data",
                  hist_df.iloc[0]["days_of_data"])
        h3.metric("Best Reliability Grade",
                  f"{hist_df.iloc[0]['observatory'].replace(' Observatory', '')[:20]} "
                  f"— {hist_df.iloc[0]['grade']}")
        h4.metric("Most Consistent Site",
                  hist_df.sort_values(
                      "consistency",
                      ascending=False
                  ).iloc[0]["observatory"].replace(
                      " Observatory", "")[:20])

        st.markdown("---")

        # Grade distribution
        st.subheader("Grade distribution")
        grade_counts = hist_df["grade"].value_counts()
        gc1, gc2, gc3, gc4, gc5 = st.columns(5)
        a_grades  = sum(grade_counts.get(g, 0)
                        for g in ["A+", "A", "A-"])
        b_grades  = sum(grade_counts.get(g, 0)
                        for g in ["B+", "B", "B-"])
        c_grades  = sum(grade_counts.get(g, 0)
                        for g in ["C+", "C", "C-"])
        d_grades  = grade_counts.get("D", 0)
        gc1.metric("A grades (Excellent)", a_grades)
        gc2.metric("B grades (Good)",      b_grades)
        gc3.metric("C grades (Average)",   c_grades)
        gc4.metric("D grades (Poor)",      d_grades)
        gc5.metric("Improving trend 📈",
                   len(hist_df[
                       hist_df["trend"].str.contains(
                           "Improving")]))

        st.markdown("---")

        # Rankings
        st.subheader(
            f"Reliability rankings — last {days_option} days")

        for _, row in hist_df.iterrows():
            grade_color = get_grade_color(row["grade"])
            trend_emoji = get_trend_emoji(row["trend"])

            with st.expander(
                f"**{row['grade']}** — "
                f"{row['observatory']} · "
                f"Reliability {row['reliability_score']}/100 · "
                f"{row['pct_excellent']}% excellent nights · "
                f"{trend_emoji} {row['trend']}"
            ):
                r1, r2, r3, r4, r5 = st.columns(5)
                r1.metric("Reliability Score",
                          f"{row['reliability_score']}/100")
                r2.metric("Average Score",
                          f"{row['avg_score']}/100")
                r3.metric("Consistency",
                          f"{row['consistency']}/100")
                r4.metric("% Excellent Nights",
                          f"{row['pct_excellent']}%")
                r5.metric("Days of Data",
                          row["days_of_data"])

                n1, n2, n3 = st.columns(3)
                n1.metric("Excellent Nights (80+)",
                          row["excellent_nights"])
                n2.metric("Good Nights (60+)",
                          row["good_nights"])
                n3.metric("Poor Nights (<40)",
                          row["poor_nights"])

                d1, d2, d3 = st.columns(3)
                d1.metric("Best Day",   row["best_day"])
                d2.metric("Worst Day",  row["worst_day"])
                d3.metric("Trend",      row["trend"])

                # Mini score history chart
                if row["daily_scores"]:
                    import matplotlib.pyplot as plt
                    import io

                    dates  = [d["fetch_date"]
                              for d in row["daily_scores"]]
                    scores = [d["daily_score"]
                              for d in row["daily_scores"]]

                    fig, ax = plt.subplots(figsize=(10, 2))
                    ax.fill_between(
                        range(len(scores)), scores,
                        alpha=0.3, color=grade_color)
                    ax.plot(
                        range(len(scores)), scores,
                        color=grade_color, linewidth=2)
                    ax.axhline(
                        y=80, color="#1D9E75",
                        linestyle="--", alpha=0.5,
                        linewidth=1, label="Excellent")
                    ax.axhline(
                        y=60, color="#378ADD",
                        linestyle="--", alpha=0.5,
                        linewidth=1, label="Good")
                    ax.set_ylim(0, 105)
                    ax.set_xticks(range(len(dates)))
                    ax.set_xticklabels(
                        dates, rotation=45, fontsize=7)
                    ax.set_ylabel("Score", fontsize=8)
                    ax.set_facecolor("#0E1117")
                    fig.patch.set_facecolor("#0E1117")
                    ax.tick_params(colors="white",
                                   labelsize=7)
                    ax.yaxis.label.set_color("white")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.spines["left"].set_color("#444441")
                    ax.spines["bottom"].set_color("#444441")
                    ax.legend(
                        fontsize=7, facecolor="#0E1117",
                        labelcolor="white",
                        loc="upper right")
                    buf = io.BytesIO()
                    plt.tight_layout()
                    plt.savefig(buf, format="png", dpi=120,
                                facecolor="#0E1117",
                                bbox_inches="tight")
                    buf.seek(0)
                    img_data = buf.getvalue()
                    buf.close()
                    plt.close()
                    st.image(img_data, width='stretch')

                st.caption(
                    f"{row['country']} · "
                    f"{row['altitude_m']}m altitude · "
                    f"Score range: {row['min_score']} — "
                    f"{row['max_score']}"
                )

        st.markdown("---")

        # Full table
        st.subheader("Complete reliability table")
        hist_display = hist_df[[
            "observatory", "country", "grade",
            "reliability_score", "avg_score",
            "consistency", "pct_excellent",
            "pct_good", "pct_poor",
            "days_of_data", "trend"
        ]].rename(columns={
            "observatory":       "Observatory",
            "country":           "Country",
            "grade":             "Grade",
            "reliability_score": "Reliability",
            "avg_score":         "Avg Score",
            "consistency":       "Consistency",
            "pct_excellent":     "% Excellent",
            "pct_good":          "% Good",
            "pct_poor":          "% Poor",
            "days_of_data":      "Days",
            "trend":             "Trend"
        })
        st.dataframe(hist_display, hide_index=True,
                     height=600)

        st.download_button(
            label="Download reliability report as CSV",
            data=hist_display.to_csv(index=False),
            file_name=f"reliability_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )
# ═══════════════════════════════════════════════════════
# TAB 7 — Site Comparison
# ═══════════════════════════════════════════════════════
with tab7:
    st.subheader("⚖️ Comparative Site Analysis")
    st.caption(
        "Select 2 to 5 observatories to compare side by side. "
        "Useful for telescope time proposals and site selection. "
        "Combines current conditions, historical reliability, "
        "atmospheric seeing, PWV, and jet stream impact."
    )

    # Observatory selector
    all_obs = df["observatory"].tolist()
    selected_sites = st.multiselect(
        "Select observatories to compare (2–5)",
        all_obs,
        default=all_obs[:3],
        max_selections=5
    )

    comp_days = st.selectbox(
        "Historical window",
        [7, 14, 30],
        index=0,
        format_func=lambda x: f"Last {x} days",
        key="comp_days"
    )

    if len(selected_sites) < 2:
        st.warning(
            "Please select at least 2 observatories to compare.")
    else:
        with st.spinner(
            f"Comparing {len(selected_sites)} sites..."
        ):
            comp_df = compare_sites(selected_sites, comp_days)

        if comp_df.empty:
            st.error("Could not load comparison data.")
        else:
            st.markdown("---")

            # ── Current conditions comparison ─────────────────
            st.subheader("Current conditions")
            cols = st.columns(len(comp_df))
            for i, (_, row) in enumerate(comp_df.iterrows()):
                with cols[i]:
                    score = row["today_score"]
                    if score >= 80:   color = "🟢"
                    elif score >= 60: color = "🔵"
                    elif score >= 40: color = "🟡"
                    else:             color = "🔴"
                    st.markdown(
                        f"### {color} {row['observatory'].replace(' Observatory', '').replace(' Telescope', '')[:20]}")
                    st.metric("Today's Score",
                              f"{score}/100")
                    st.metric("Cloud Cover",
                              f"{row['cloud_cover_pct']}%")
                    st.metric("Humidity",
                              f"{row['humidity_pct']}%")
                    st.metric("Wind Speed",
                              f"{row['wind_speed_ms']} m/s")
                    st.metric("Temperature",
                              f"{row['temperature_c']}°C")

            st.markdown("---")

            # ── Atmospheric comparison ────────────────────────
            st.subheader("Atmospheric conditions")
            cols2 = st.columns(len(comp_df))
            for i, (_, row) in enumerate(comp_df.iterrows()):
                with cols2[i]:
                    st.markdown(
                        f"**{row['observatory'].replace(' Observatory', '')[:20]}**")
                    st.metric("Seeing",
                              f"{row['seeing_arcsec']}\"",
                              row["seeing_quality"])
                    st.metric("PWV",
                              f"{row['pwv_mm']} mm",
                              row["pwv_quality"])
                    st.metric("Jet Stream",
                              f"{row['jet_stream_ms']} m/s",
                              row["jet_impact"])
                    st.metric("Altitude",
                              f"{row['altitude_m']}m")

            st.markdown("---")

            # ── Historical comparison chart ───────────────────
            st.subheader(
                f"Score history — last {comp_days} days")

            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import io

            colors_palette = [
                "#1D9E75", "#378ADD", "#EF9F27",
                "#E24B4A", "#AFA9EC"
            ]

            fig, ax = plt.subplots(figsize=(12, 5))

            has_history = False
            for i, (_, row) in enumerate(comp_df.iterrows()):
                if row["daily_scores"]:
                    has_history = True
                    dates  = [d["fetch_date"]
                              for d in row["daily_scores"]]
                    scores = [d["daily_score"]
                              for d in row["daily_scores"]]
                    color  = colors_palette[
                        i % len(colors_palette)]
                    label  = row["observatory"].replace(
                        " Observatory", "").replace(
                        " Telescope", "")[:25]
                    ax.plot(range(len(scores)), scores,
                            color=color, linewidth=2,
                            marker="o", markersize=4,
                            label=label)
                    ax.fill_between(
                        range(len(scores)), scores,
                        alpha=0.1, color=color)

            if has_history:
                ax.axhline(y=80, color="#1D9E75",
                           linestyle="--", alpha=0.4,
                           linewidth=1, label="Excellent (80)")
                ax.axhline(y=60, color="#378ADD",
                           linestyle="--", alpha=0.4,
                           linewidth=1, label="Good (60)")
                ax.set_ylim(0, 105)
                ax.set_ylabel("Observation Score",
                              fontsize=10)
                ax.set_title(
                    "Historical Score Comparison",
                    fontsize=12, fontweight="bold")
                ax.legend(fontsize=9,
                          facecolor="#0E1117",
                          labelcolor="white",
                          loc="upper right")
                ax.set_facecolor("#0E1117")
                fig.patch.set_facecolor("#0E1117")
                ax.tick_params(colors="white")
                ax.yaxis.label.set_color("white")
                ax.title.set_color("white")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("#444441")
                ax.spines["bottom"].set_color("#444441")

                buf = io.BytesIO()
                plt.tight_layout()
                plt.savefig(buf, format="png", dpi=120,
                    facecolor="#0E1117",
                    bbox_inches="tight")
                buf.seek(0)
                img_data = buf.getvalue()
                buf.close()
                plt.close()
                st.image(img_data, width='stretch')
            else:
                st.info(
                    "Not enough historical data yet. "
                    "Come back after a few days of pipeline "
                    "runs to see score trends here."
                )

            st.markdown("---")

            # ── Bar chart comparison ──────────────────────────
            st.subheader("Side by side metrics comparison")

            metrics = {
                "Today's Score":    "today_score",
                "Avg Score":        "avg_score",
                "% Excellent":      "pct_excellent",
                "Consistency":      "consistency",
                "Seeing (inverted)": "seeing_arcsec",
                "PWV (inverted)":   "pwv_mm"
            }

            fig2, axes = plt.subplots(
                2, 3, figsize=(14, 8))
            axes = axes.flatten()
            names = [
                r["observatory"].replace(
                    " Observatory", "").replace(
                    " Telescope", "")[:15]
                for _, r in comp_df.iterrows()
            ]

            for idx, (label, col) in enumerate(
                metrics.items()
            ):
                ax = axes[idx]
                vals = comp_df[col].tolist()

                # Invert seeing and PWV
                # (lower is better so invert for chart)
                if "inverted" in label:
                    plot_vals = [
                        max(0, 100 - v * 10)
                        if v is not None else 0
                        for v in vals
                    ]
                else:
                    plot_vals = [
                        v if v is not None else 0
                        for v in vals
                    ]

                bar_colors = [
                    colors_palette[i % len(colors_palette)]
                    for i in range(len(names))
                ]
                bars = ax.bar(names, plot_vals,
                              color=bar_colors, width=0.6)

                for bar, val in zip(bars, vals):
                    display = (
                        f"{val}\"" if "Seeing" in label
                        else f"{val}mm" if "PWV" in label
                        else f"{val}"
                    )
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 1,
                        display,
                        ha="center", va="bottom",
                        fontsize=8, color="white"
                    )

                ax.set_title(label, fontsize=10,
                             fontweight="bold",
                             color="white")
                ax.set_ylim(0, 110)
                ax.set_facecolor("#0E1117")
                ax.tick_params(colors="white", labelsize=8)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("#444441")
                ax.spines["bottom"].set_color("#444441")
                ax.tick_params(axis="x", rotation=15)

            fig2.patch.set_facecolor("#0E1117")
            fig2.suptitle(
                "Observatory Comparison Dashboard",
                fontsize=14, fontweight="bold",
                color="white", y=1.02)
            buf2 = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf2, format="png", dpi=150,
                        facecolor="#0E1117",
                        bbox_inches="tight")
            buf2.seek(0)
            st.image(buf2.getvalue(), width='stretch')
            plt.close()

            st.markdown("---")

            # ── Full comparison table ─────────────────────────
            st.subheader("Full comparison table")
            comp_display = comp_df[[
                "observatory", "country", "altitude_m",
                "today_score", "avg_score", "pct_excellent",
                "consistency", "seeing_arcsec", "pwv_mm",
                "jet_stream_ms", "jet_impact", "days_of_data"
            ]].rename(columns={
                "observatory":   "Observatory",
                "country":       "Country",
                "altitude_m":    "Altitude (m)",
                "today_score":   "Today",
                "avg_score":     "Avg Score",
                "pct_excellent": "% Excellent",
                "consistency":   "Consistency",
                "seeing_arcsec": "Seeing (\")",
                "pwv_mm":        "PWV (mm)",
                "jet_stream_ms": "Jet (m/s)",
                "jet_impact":    "Jet Impact",
                "days_of_data":  "Days"
            })
            st.dataframe(comp_display,
                         hide_index=True, height=300)

            # Download
            st.download_button(
                label="Download comparison as CSV",
                data=comp_display.to_csv(index=False),
                file_name=f"site_comparison_"
                          f"{utcnow().strftime('%Y-%m-%d')}"
                          f".csv",
                mime="text/csv"
            )

            # ── Proposal helper text ──────────────────────────
            st.markdown("---")
            st.subheader("📝 Proposal helper")
            st.caption(
                "Auto-generated text you can use in a telescope "
                "time proposal to justify your site selection."
            )

            best = comp_df.iloc[0]
            proposal_text = f"""
Based on atmospheric monitoring data collected over the past {comp_days} days, {best['observatory']} demonstrates superior observing conditions compared to the {len(comp_df)-1} alternative site(s) considered.

{best['observatory']} achieved an average observation quality score of {best['avg_score']}/100, with {best['pct_excellent']}% of monitored nights classified as excellent (score ≥ 80). The estimated atmospheric seeing of {best['seeing_arcsec']} arcseconds and precipitable water vapor of {best['pwv_mm']} mm place this site in the {best['seeing_quality']} category for optical observation quality.

The jet stream impact at this site is currently assessed as {best['jet_impact']} at {best['jet_stream_ms']} m/s at 250hPa, indicating {'minimal' if best['jet_impact'] in ['Negligible', 'Low'] else 'moderate to significant'} upper-atmosphere turbulence.

At {best['altitude_m']}m elevation in {best['country']}, this site {'benefits from reduced atmospheric water vapor compared to lower-altitude alternatives' if best['altitude_m'] > 2000 else 'provides accessible infrastructure while maintaining acceptable atmospheric conditions'}.

Data sourced from automated atmospheric monitoring pipeline (Open-Meteo API) with daily updates via GitHub Actions.
            """.strip()

            st.text_area(
                "Copy this into your proposal",
                proposal_text,
                height=250
            )

# ═══════════════════════════════════════════════════════
# TAB 8 — Semester Planning Calendar
# ═══════════════════════════════════════════════════════
with tab8:
    st.subheader("📅 Semester Planning Calendar")
    st.caption(
        "Plan your observing semester months in advance. "
        "Shows predicted observation quality for every day "
        "based on moon phase and dark hours. "
        "Actual recorded scores shown where available."
    )

    # Controls
    sp1, sp2, sp3 = st.columns(3)
    with sp1:
        sem_obs = st.selectbox(
            "Select observatory",
            df["observatory"].tolist(),
            key="sem_obs"
        )
    with sp2:
        current_year = utcnow().year
        sem_year = st.selectbox(
            "Year",
            [current_year, current_year + 1],
            key="sem_year"
        )
    with sp3:
        sem_months = st.selectbox(
            "Months to show",
            [3, 6, 9, 12],
            index=1,
            key="sem_months"
        )

    start_month = st.selectbox(
        "Starting month",
        list(range(1, 13)),
        index=utcnow().month - 1,
        format_func=lambda x: calendar.month_name[x],
        key="sem_start"
    )

    with st.spinner(
        f"Building {sem_months}-month calendar for "
        f"{sem_obs}..."
    ):
        cal_data  = build_calendar_data(
            sem_obs, sem_year, start_month, sem_months)
        best_months = get_best_months(
            sem_obs, sem_year, sem_months)

    st.markdown("---")

    # Best months summary
    st.subheader("Best months for observing")
    bm_cols = st.columns(min(4, len(best_months)))
    for i, (_, row) in enumerate(
        best_months.head(4).iterrows()
    ):
        with bm_cols[i]:
            st.metric(
                row["month"],
                f"{row['excellent_days']} excellent days",
                f"Avg {row['avg_score']}/100"
            )

    st.markdown("---")

    # Monthly bar chart
    st.subheader("Monthly excellent days comparison")
    import matplotlib.pyplot as plt
    import io
    import calendar as cal_module

    fig, ax = plt.subplots(figsize=(12, 4))
    month_names  = best_months["month"].tolist()
    exc_days     = best_months["excellent_days"].tolist()
    good_days    = best_months["good_days"].tolist()

    x      = range(len(month_names))
    width  = 0.35
    bars1  = ax.bar(
        [i - width/2 for i in x], exc_days,
        width, label="Excellent nights",
        color="#1D9E75", alpha=0.9)
    bars2  = ax.bar(
        [i + width/2 for i in x], good_days,
        width, label="Good nights",
        color="#378ADD", alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(month_names, rotation=45,
                       fontsize=9, color="white")
    ax.set_ylabel("Number of nights", color="white")
    ax.set_title(
        f"Observing Quality by Month — {sem_obs}",
        fontsize=12, fontweight="bold", color="white")
    ax.legend(facecolor="#0E1117", labelcolor="white",
              fontsize=9)
    ax.set_facecolor("#0E1117")
    fig.patch.set_facecolor("#0E1117")
    ax.tick_params(colors="white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444441")
    ax.spines["bottom"].set_color("#444441")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150,
                facecolor="#0E1117", bbox_inches="tight")
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()
    st.image(img_data, width='stretch')
    plt.close()

    st.markdown("---")

    # Calendar heatmap for each month
    st.subheader("Day by day calendar heatmap")
    st.caption(
        "🟢 Excellent · 🔵 Good · 🟡 Marginal · 🔴 Poor · "
        "Bold = actual recorded data · Normal = estimated"
    )

    color_map = {
        "Excellent": "#1D9E75",
        "Good":      "#378ADD",
        "Marginal":  "#EF9F27",
        "Poor":      "#E24B4A"
    }

    for month_key, month_data in cal_data.items():
        st.markdown(
            f"### {month_data['month_name']} "
            f"{month_data['year']}"
        )

        summary = month_data["summary"]
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Avg Score",
                   f"{summary['avg_score']}/100")
        sc2.metric("Excellent Days",
                   summary["excellent_days"])
        sc3.metric("Good Days",
                   summary["good_days"])
        sc4.metric("New Moon Days",
                   summary["new_moon_days"])

        # Build calendar grid
        days      = month_data["days"]
        first_day = days[0]["weekday"]

        # Header
        day_cols = st.columns(7)
        for i, d in enumerate(
            ["Mon", "Tue", "Wed", "Thu",
             "Fri", "Sat", "Sun"]
        ):
            day_cols[i].markdown(
                f"<div style='text-align:center;"
                f"color:#888780;font-size:12px'>"
                f"<b>{d}</b></div>",
                unsafe_allow_html=True
            )

        # Calendar rows
        week_days = [None] * first_day + days
        while len(week_days) % 7 != 0:
            week_days.append(None)

        for week_start in range(
            0, len(week_days), 7
        ):
            week = week_days[week_start:week_start + 7]
            cols = st.columns(7)
            for i, day_data in enumerate(week):
                if day_data is None:
                    cols[i].markdown(" ")
                else:
                    color    = color_map.get(
                        day_data["quality"], "#888780")
                    score    = day_data["moon_adj_score"]
                    day_num  = day_data["day"]
                    moon_pct = day_data["moon_pct"]
                    is_today = (
                        day_data["date"] ==
                        utcnow().strftime(
                            "%Y-%m-%d"))
                    border   = (
                        "3px solid white"
                        if is_today
                        else "1px solid #333"
                    )
                    actual   = "★" if day_data[
                        "is_actual"] else ""

                    cols[i].markdown(
                        f"<div style='"
                        f"background:{color}22;"
                        f"border:{border};"
                        f"border-radius:6px;"
                        f"padding:4px;"
                        f"text-align:center;"
                        f"margin:1px'>"
                        f"<span style='color:{color};"
                        f"font-weight:bold;"
                        f"font-size:13px'>"
                        f"{day_num}{actual}</span><br>"
                        f"<span style='font-size:10px;"
                        f"color:#ccc'>{score}</span><br>"
                        f"<span style='font-size:9px;"
                        f"color:#888'>"
                        f"🌙{moon_pct:.0f}%</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        st.markdown("---")

    # Semester recommendation
    st.subheader("📝 Semester recommendation")
    best_m   = best_months.iloc[0]
    worst_m  = best_months.iloc[-1]
    obs_name = sem_obs.replace(" Observatory", "").replace(
        " Telescope", "")

    recommendation = f"""
SEMESTER OBSERVING RECOMMENDATION — {sem_obs.upper()}

Best semester: {best_m['month']} {best_m['year']}
— {best_m['excellent_days']} excellent nights expected
— {best_m['good_days']} good nights expected
— Average quality score: {best_m['avg_score']}/100
— Best single night: {best_m['best_day']}

Avoid: {worst_m['month']} {worst_m['year']}
— Only {worst_m['excellent_days']} excellent nights expected
— Average quality score: {worst_m['avg_score']}/100

Key scheduling notes:
— New moon periods offer the darkest skies for faint objects
— Plan deep sky observations around new moon ± 5 days
— Bright object work (planets, doubles) can use any phase
— Allow 20% buffer for unexpected poor weather nights

Data confidence: {'High — based on actual recorded data' 
if any(d['is_actual'] for month in cal_data.values() 
       for d in month['days']) 
else 'Estimated — based on astronomical calculations'}

Generated by Global Observatory Weather Tracker
{utcnow().strftime('%Y-%m-%d %H:%M')} UTC
    """.strip()

    st.text_area(
        "Copy for your proposal or planning document",
        recommendation,
        height=300
    )

    st.download_button(
        label="Download semester plan as CSV",
        data=best_months.to_csv(index=False),
        file_name=f"semester_plan_{sem_obs.replace(' ', '_')}_"
                  f"{sem_year}.csv",
        mime="text/csv"
    )

# ═══════════════════════════════════════════════════════
# TAB 9 — Educational Mode
# ═══════════════════════════════════════════════════════
with tab9:
    st.subheader("🎓 Learn Astronomy — Educational Mode")
    st.caption(
        "Understand every metric on this dashboard. "
        "From cloud cover to jet streams — explained for "
        "students, educators, and curious minds."
    )

    categories = get_concepts_by_category()
    concepts   = get_all_concepts()

    # Category filter
    selected_category = st.selectbox(
        "Browse by category",
        ["All"] + list(categories.keys())
    )

    if selected_category == "All":
        concept_keys = list(concepts.keys())
    else:
        concept_keys = categories[selected_category]

    st.markdown("---")

    # Search
    search = st.text_input(
        "🔍 Search concepts",
        placeholder="e.g. seeing, humidity, moon..."
    )

    if search:
        concept_keys = [
            k for k in concept_keys
            if search.lower() in k.lower()
            or search.lower() in concepts[k][
                "title"].lower()
            or search.lower() in concepts[k][
                "simple"].lower()
        ]

    if not concept_keys:
        st.warning(
            "No concepts found. Try a different search term.")
    else:
        # Quick reference cards
        st.subheader(
            f"{'All concepts' if selected_category == 'All' else selected_category} "
            f"— {len(concept_keys)} topics"
        )

        for key in concept_keys:
            concept = concepts[key]
            with st.expander(
                f"{concept['emoji']} "
                f"**{concept['title']}** — "
                f"{concept['simple']}"
            ):
                col_left, col_right = st.columns([2, 1])

                with col_left:
                    st.markdown("**What it means**")
                    st.markdown(concept["simple"])
                    st.markdown("---")
                    st.markdown("**In depth**")
                    st.markdown(concept["detailed"])

                with col_right:
                    st.markdown("**Quick reference**")
                    st.info(
                        f"**Unit:** {concept['symbol']}\n\n"
                        f"**Role:** {concept['weight']}"
                    )
                    if concept.get("formula"):
                        st.markdown("**Formula used**")
                        st.code(concept["formula"])
                    if concept.get("fun_fact"):
                        st.success(
                            f"💡 **Did you know?**\n\n"
                            f"{concept['fun_fact']}"
                        )

    st.markdown("---")

    # Live explainer — connect concepts to real data
    st.subheader(
        "🔴 Live — understand tonight's data")
    st.caption(
        "See exactly how each concept applies to "
        "real conditions right now."
    )

    live_obs = st.selectbox(
        "Pick an observatory to explain",
        df["observatory"].tolist(),
        key="edu_obs"
    )

    live_row = df[
        df["observatory"] == live_obs].iloc[0]
    score    = live_row["observation_score"]
    cloud    = live_row["cloud_cover_pct"]
    humidity = live_row["humidity_pct"]
    wind     = live_row["wind_speed_ms"]
    temp     = live_row["temperature_c"]

    st.markdown(
        f"### {live_obs} — right now")

    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Score", f"{score}/100")
    e2.metric("Cloud", f"{cloud}%")
    e3.metric("Humidity", f"{humidity}%")
    e4.metric("Wind", f"{wind} m/s")

    st.markdown("---")
    st.markdown("**What this means in plain English:**")

    # Cloud explanation
    if cloud <= 10:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — the sky is essentially clear. This is ideal for all types of observation."
    elif cloud <= 30:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — mostly clear with some thin cloud. Faint objects may be slightly affected."
    elif cloud <= 60:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — partly cloudy. Only bright objects like planets and bright stars are reliable targets tonight."
    else:
        cloud_msg = f"☁️ Cloud cover is {cloud}% — heavily clouded. The dome at this observatory would likely be closed right now."
    st.info(cloud_msg)

    # Humidity explanation
    if humidity <= 50:
        hum_msg = f"💧 Humidity is {humidity}% — very dry air. Mirrors and lenses are safe from condensation. Excellent transparency."
    elif humidity <= 70:
        hum_msg = f"💧 Humidity is {humidity}% — acceptable. No immediate risk to optics but worth monitoring."
    elif humidity <= 85:
        hum_msg = f"💧 Humidity is {humidity}% — getting high. Operators will be watching carefully. Dew heaters on the telescope will be active."
    else:
        hum_msg = f"💧 Humidity is {humidity}% — above the 85% safety threshold. Real observatories would close or have already closed the dome to protect the mirrors."
    st.info(hum_msg)

    # Wind explanation
    if wind <= 5:
        wind_msg = f"💨 Wind is {wind} m/s — essentially calm. No mechanical vibration. Images will be sharp and stable."
    elif wind <= 10:
        wind_msg = f"💨 Wind is {wind} m/s — light breeze. Negligible effect on most telescopes. Larger dishes may show very slight motion."
    elif wind <= 15:
        wind_msg = f"💨 Wind is {wind} m/s — moderate wind. Smaller telescopes may show vibration. Large professional scopes can still operate."
    else:
        wind_msg = f"💨 Wind is {wind} m/s — above the 15 m/s threshold used in our scoring. Most professional observatories would close or restrict operations at this wind speed."
    st.info(wind_msg)

    # Score explanation
    if score >= 80:
        score_msg = f"⭐ Overall score is {score}/100 — Excellent. This is a good night for serious astronomy. Deep sky objects, faint galaxies, and nebulae are all viable targets."
    elif score >= 60:
        score_msg = f"⭐ Overall score is {score}/100 — Good. Suitable for most observation programmes. Bright targets will be sharp and photometry is reliable."
    elif score >= 40:
        score_msg = f"⭐ Overall score is {score}/100 — Marginal. Only bright targets recommended. Students can still observe planets and the Moon, but faint deep sky work is not advised."
    else:
        score_msg = f"⭐ Overall score is {score}/100 — Poor. Observing is not recommended tonight at this site. A real observatory operator would keep the dome closed."
    st.success(score_msg)

    st.markdown("---")

    # Glossary
    st.subheader("📖 Quick glossary")
    glossary = {
        "Arcsecond (\")":      "1/3600 of a degree. Unit for measuring very small angles in the sky.",
        "Aperture":            "The diameter of a telescope's main mirror or lens. Larger = more light collected.",
        "Seeing":              "Atmospheric turbulence that blurs stellar images. Measured in arcseconds.",
        "PWV":                 "Precipitable Water Vapor. Total water in atmosphere above telescope. Critical for infrared.",
        "Photometry":          "Precise measurement of a star's brightness. Requires stable, clear conditions.",
        "Spectroscopy":        "Splitting starlight into its spectrum to measure composition, temperature, velocity.",
        "Limiting magnitude":  "The faintest star visible under given conditions. Higher number = fainter stars seen.",
        "Inversion layer":     "A layer of warm air trapping cool air below. Mauna Kea sits above Hawaii's inversion layer.",
        "Dome seeing":         "Turbulence caused by warm air inside the telescope dome mixing with cold outside air.",
        "Meridian":            "The imaginary line across the sky directly overhead, north to south. Objects are highest here.",
        "Zenith":              "The point directly overhead. Objects at zenith have the least atmosphere to look through.",
        "Airmass":             "How much atmosphere the telescope looks through. 1.0 at zenith, increases toward horizon.",
        "Declination":         "Celestial equivalent of latitude. How far north or south of the celestial equator.",
        "Right Ascension":     "Celestial equivalent of longitude. Measured in hours, minutes, seconds.",
        "Altitude":            "Height above the horizon in degrees. 0° = horizon, 90° = zenith.",
        "Azimuth":             "Compass direction of an object. 0° = North, 90° = East, 180° = South, 270° = West.",
    }

    for term, definition in glossary.items():
        st.markdown(f"**{term}** — {definition}")

# ═══════════════════════════════════════════════════════
# TAB 10 — Alert Subscriptions
# ═══════════════════════════════════════════════════════
with tab10:
    st.subheader("🔔 Alert Subscriptions")
    st.caption(
        "Get emailed automatically when observing conditions "
        "at your chosen observatory cross a threshold. "
        "Alerts are checked daily at 06:00 UTC."
    )

    # ── Subscribe form ────────────────────────────────────
    st.subheader("Subscribe to alerts")
    with st.form("subscribe_form"):
        sub_email = st.text_input(
            "Your email address",
            placeholder="you@example.com"
        )
        sub_obs = st.selectbox(
            "Observatory to monitor",
            df["observatory"].tolist(),
            key="sub_obs"
        )
        sub_threshold = st.slider(
            "Alert threshold (score)",
            min_value=40,
            max_value=95,
            value=80,
            step=5,
            help="You will be alerted when the score crosses this value"
        )
        sub_type = st.radio(
            "Alert me when score is",
            ["Above threshold (good conditions)",
             "Below threshold (poor conditions)"],
            help="Above = notify when it gets good. Below = notify when it gets bad."
        )
        submitted = st.form_submit_button(
            "Subscribe", type="primary")

        if submitted:
            if not sub_email or "@" not in sub_email:
                st.error(
                    "Please enter a valid email address.")
            else:
                alert_type = (
                    "above"
                    if "Above" in sub_type
                    else "below"
                )
                success, msg = add_subscription(
                    sub_email, sub_obs,
                    sub_threshold, alert_type
                )
                if success:
                    st.success(
                        f"✅ Subscribed! You will receive "
                        f"an email when {sub_obs} scores "
                        f"{'above' if alert_type == 'above' else 'below'} "
                        f"{sub_threshold}/100."
                    )
                else:
                    st.warning(msg)

    st.markdown("---")

    # ── Unsubscribe ───────────────────────────────────────
    st.subheader("Unsubscribe")
    with st.form("unsubscribe_form"):
        unsub_email = st.text_input(
            "Your email address",
            placeholder="you@example.com",
            key="unsub_email"
        )
        unsub_obs = st.selectbox(
            "Observatory",
            df["observatory"].tolist(),
            key="unsub_obs"
        )
        unsub_submitted = st.form_submit_button(
            "Unsubscribe")

        if unsub_submitted:
            removed = remove_subscription(
                unsub_email, unsub_obs)
            if removed:
                st.success(
                    f"✅ Unsubscribed from {unsub_obs}.")
            else:
                st.error(
                    "Subscription not found.")

    st.markdown("---")

    # ── Current subscriptions ─────────────────────────────
    st.subheader("Active subscriptions")
    subs = load_subscriptions()

    if not subs:
        st.info(
            "No active subscriptions yet. "
            "Be the first to subscribe above!")
    else:
        active = [s for s in subs if s.get("active", True)]
        st.metric("Total subscriptions", len(active))

        for sub in active:
            obs_score = df[
                df["observatory"] == sub["observatory"]
            ]
            current_score = (
                obs_score.iloc[0]["observation_score"]
                if not obs_score.empty else "N/A"
            )
            alert_type = sub.get("alert_type", "above")

            with st.expander(
                f"📧 {sub['email']} → "
                f"{sub['observatory']} · "
                f"{'Above' if alert_type == 'above' else 'Below'} "
                f"{sub['threshold']}/100 · "
                f"Current score: {current_score}"
            ):
                s1, s2, s3, s4 = st.columns(4)
                s1.metric(
                    "Threshold",
                    f"{sub['threshold']}/100")
                s2.metric(
                    "Alert type",
                    "Above ↑" if alert_type == "above"
                    else "Below ↓")
                s3.metric(
                    "Current score",
                    f"{current_score}/100")
                s4.metric(
                    "Last alerted",
                    sub.get("last_alerted", "Never"
                            )[:10] if sub.get(
                        "last_alerted") else "Never"
                )
                st.caption(
                    f"Subscribed: "
                    f"{sub.get('created_at', '')[:10]}"
                )

    st.markdown("---")

    # ── How it works ──────────────────────────────────────
    st.subheader("How alerts work")
    st.markdown("""
**1. Subscribe** — Enter your email, choose an observatory
and a threshold score.

**2. Daily check** — Every day at 06:00 UTC, the pipeline
fetches fresh weather data for all 95 observatories.

**3. Comparison** — Your threshold is compared against
the current observation quality score.

**4. Email sent** — If conditions cross your threshold,
you receive a beautifully formatted email with full
weather details and an observing tip.

**Alert types:**
- **Above threshold** — Great for planning. Get notified
  when your favourite site reaches excellent conditions.
- **Below threshold** — Great for operators. Get notified
  when conditions drop, so you know to close the dome.

**Frequency** — Maximum one alert per subscription per day.
    """)
# ═══════════════════════════════════════════════════════
# TAB 11 — Telescope Efficiency
# ═══════════════════════════════════════════════════════
with tab11:
    st.subheader("🏆 Telescope Efficiency Score")
    st.caption(
        "The single most important number for planning. "
        "Combines weather quality, dark hours, moon position, "
        "seeing, PWV and jet stream into one efficiency score. "
        "Answers: how many truly usable hours will this "
        "telescope produce tonight?"
    )

    # Telescope type selector
    tel_type = st.radio(
        "Telescope type",
        ["Optical", "Infrared", "Radio"],
        horizontal=True,
        help="Different telescope types weight atmospheric "
             "conditions differently"
    )
    tel_type_key = tel_type.lower()

    type_explanations = {
        "Optical":  "Weighted for cloud cover (40%), dark hours (25%), moon (15%), seeing (12%)",
        "Infrared": "Weighted for PWV (25%), cloud cover (30%), dark hours (20%), seeing (8%)",
        "Radio":    "Weighted for PWV (45%), jet stream (20%), cloud cover (20%) — can observe through clouds"
    }
    st.info(f"**{tel_type}:** {type_explanations[tel_type]}")

    with st.spinner(
        f"Calculating {tel_type} telescope efficiency "
        f"for all 95 observatories..."
    ):
        eff_df = load_efficiency_cached(tel_type_key)

    if eff_df.empty:
        st.error("No data available.")
    else:
        # Summary metrics
        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric(
            "Best Site Tonight",
            eff_df.iloc[0]["observatory"].replace(
                " Observatory", "")[:18]
        )
        e2.metric(
            "Top Efficiency Score",
            f"{eff_df.iloc[0]['efficiency_score']}/100"
        )
        e3.metric(
            "Top Grade",
            eff_df.iloc[0]["grade"]
        )
        e4.metric(
            "Max Usable Hours",
            f"{eff_df.iloc[0]['usable_hours']}h"
        )
        e5.metric(
            "A-grade Sites",
            len(eff_df[eff_df["grade"].isin(
                ["A+", "A", "A-"])])
        )

        st.markdown("---")

        # World map coloured by efficiency
        st.subheader(
            f"World map — {tel_type} telescope efficiency")

        m_eff = folium.Map(
            location=[20, 0], zoom_start=2,
            tiles="CartoDB positron"
        )

        for _, row in eff_df.iterrows():
            score = row["efficiency_score"]
            if score >= 80:   color = "#1D9E75"
            elif score >= 65: color = "#378ADD"
            elif score >= 50: color = "#EF9F27"
            else:             color = "#E24B4A"

            popup_html = f"""
                <div style='font-family:sans-serif;
                            width:220px'>
                    <b>{row['observatory']}</b><br>
                    {row['country']} · {row['altitude_m']}m
                    <hr style='margin:4px 0'>
                    <b>Efficiency: {row['efficiency_score']}/100
                    [{row['grade']}]</b><br>
                    Usable hours: {row['usable_hours']}h<br>
                    Dark hours: {row['dark_hours']}h<br>
                    Moon-free: {row['moon_free_pct']}%<br>
                    Weather: {row['weather_score']}/100<br>
                    Seeing: {row['seeing_arcsec']}"<br>
                    PWV: {row['pwv_mm']}mm<br>
                    Jet: {row['jet_impact']}
                </div>
            """
            folium.CircleMarker(
                location=[row["latitude"],
                          row["longitude"]],
                radius=9,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                popup=folium.Popup(
                    popup_html, max_width=230),
                tooltip=f"{row['observatory']} — "
                        f"{row['efficiency_score']}/100 "
                        f"[{row['grade']}] · "
                        f"{row['usable_hours']}h usable"
            ).add_to(m_eff)

        st_folium(m_eff, width=None, height=480)

        ec1, ec2, ec3, ec4 = st.columns(4)
        ec1.markdown("🟢 **A grade** — 80+")
        ec2.markdown("🔵 **B grade** — 65–79")
        ec3.markdown("🟡 **C grade** — 50–64")
        ec4.markdown("🔴 **D grade** — below 50")

        st.markdown("---")

        # Rankings
        st.subheader(
            f"Efficiency rankings — {tel_type} telescopes")

        for _, row in eff_df.head(15).iterrows():
            grade = row["grade"]
            if grade in ["A+", "A"]:   emoji = "🟢"
            elif grade == "A-":         emoji = "🟢"
            elif grade in ["B+", "B"]: emoji = "🔵"
            elif grade == "B-":         emoji = "🔵"
            elif grade in ["C+", "C"]: emoji = "🟡"
            else:                       emoji = "🔴"

            with st.expander(
                f"{emoji} **{grade}** — "
                f"{row['observatory']} · "
                f"Efficiency {row['efficiency_score']}/100 · "
                f"{row['usable_hours']}h usable tonight"
            ):
                r1, r2, r3, r4, r5 = st.columns(5)
                r1.metric("Efficiency",
                          f"{row['efficiency_score']}/100")
                r2.metric("Usable Hours",
                          f"{row['usable_hours']}h")
                r3.metric("Dark Hours",
                          f"{row['dark_hours']}h")
                r4.metric("Moon-free",
                          f"{row['moon_free_pct']}%")
                r5.metric("Weather Score",
                          f"{row['weather_score']}/100")

                st.markdown("**Score breakdown**")

                components = row.get("components", {
                   "weather": 0, "dark": 0, "moon": 0,
                   "seeing": 0, "pwv": 0, "jet": 0,
                   "altitude_bonus": 0
              })
                if isinstance(components, str):
                    import json
                    components = json.loads(components)
                comp_cols  = st.columns(
                    len(components))
                labels = {
                    "weather":        "Weather",
                    "dark":           "Dark hours",
                    "moon":           "Moon",
                    "seeing":         "Seeing",
                    "pwv":            "PWV",
                    "jet":            "Jet stream",
                    "altitude_bonus": "Altitude"
                }
                for i, (key, val) in enumerate(
                    components.items()
                ):
                    comp_cols[i].metric(
                        labels.get(key, key),
                        f"+{val}"
                    )

                # Component bar chart
                import matplotlib.pyplot as plt
                import io

                fig, ax = plt.subplots(figsize=(8, 2))
                keys    = list(labels.values())
                vals    = list(components.values())
                colors_comp = [
                    "#1D9E75", "#378ADD", "#AFA9EC",
                    "#5DCAA5", "#85B7EB", "#EF9F27",
                    "#9FE1CB"
                ]
                ax.barh(keys, vals,
                        color=colors_comp[:len(keys)],
                        height=0.6)
                ax.set_xlim(0, 45)
                ax.set_xlabel("Points contributed",
                              fontsize=8, color="white")
                ax.set_facecolor("#0E1117")
                fig.patch.set_facecolor("#0E1117")
                ax.tick_params(colors="white",
                               labelsize=8)
                ax.xaxis.label.set_color("white")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("#444441")
                ax.spines["bottom"].set_color("#444441")

                buf = io.BytesIO()
                plt.tight_layout()
                plt.savefig(buf, format="png", dpi=120,
                            facecolor="#0E1117",
                            bbox_inches="tight")
                buf.seek(0)
                img_data = buf.getvalue()
                buf.close()   
                st.image(img_data, width='stretch')
                plt.close()

                st.caption(
                    f"{row['country']} · "
                    f"{row['altitude_m']}m · "
                    f"Seeing {row['seeing_arcsec']}\" · "
                    f"PWV {row['pwv_mm']}mm · "
                    f"Jet {row['jet_impact']}"
                )

        st.markdown("---")

        # Full table
        st.subheader("Complete efficiency table")
        eff_display = eff_df[[
            "observatory", "country", "grade",
            "efficiency_score", "usable_hours",
            "dark_hours", "moon_free_pct",
            "weather_score", "seeing_arcsec",
            "pwv_mm", "jet_impact"
        ]].rename(columns={
            "observatory":      "Observatory",
            "country":          "Country",
            "grade":            "Grade",
            "efficiency_score": "Efficiency",
            "usable_hours":     "Usable Hrs",
            "dark_hours":       "Dark Hrs",
            "moon_free_pct":    "Moon-free %",
            "weather_score":    "Weather",
            "seeing_arcsec":    "Seeing (\")",
            "pwv_mm":           "PWV (mm)",
            "jet_impact":       "Jet Impact"
        })
        st.dataframe(
            eff_display, hide_index=True, height=500)

        st.download_button(
            label=f"Download {tel_type} efficiency "
                  f"report as CSV",
            data=eff_display.to_csv(index=False),
            file_name=f"efficiency_{tel_type_key}_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )
        st.markdown("---")

        # ── Cross type comparison ─────────────────────
        st.subheader(
            "🔀 Cross-telescope type comparison")
        st.caption(
            "See how the same observatory ranks "
            "differently for optical, infrared and "
            "radio telescopes. Sites with high rank "
            "spread are highly specialised."
        )

        show_comparison = st.toggle(
            "Show full cross-type comparison "
            "(takes ~30 seconds to calculate)",
            value=False,
            key="cross_compare"
        )

        if show_comparison:
            with st.spinner(
                "Calculating all three telescope "
                "types for all 95 observatories..."
            ):
                from telescope_efficiency import (
                    get_cross_type_comparison)
                cross_df = get_cross_type_comparison()

            if not cross_df.empty:

                # Summary stats
                x1, x2, x3 = st.columns(3)
                best_optical  = cross_df.sort_values(
                    "optical_score",
                    ascending=False).iloc[0]
                best_infrared = cross_df.sort_values(
                    "infrared_score",
                    ascending=False).iloc[0]
                best_radio    = cross_df.sort_values(
                    "radio_score",
                    ascending=False).iloc[0]

                x1.metric(
                    "🔭 Best optical site tonight",
                    best_optical["observatory"].replace(
                        " Observatory", "")[:20],
                    f"{best_optical['optical_score']}/100"
                )
                x2.metric(
                    "🌡️ Best infrared site tonight",
                    best_infrared["observatory"].replace(
                        " Observatory", "")[:20],
                    f"{best_infrared['infrared_score']}/100"
                )
                x3.metric(
                    "📡 Best radio site tonight",
                    best_radio["observatory"].replace(
                        " Observatory", "")[:20],
                    f"{best_radio['radio_score']}/100"
                )

                st.markdown("---")

                # Most specialised sites
                st.subheader(
                    "Most specialised observatories")
                st.caption(
                    "High rank spread means the site "
                    "is dramatically better for one "
                    "telescope type than others."
                )

                specialised = cross_df.sort_values(
                    "rank_spread", ascending=False
                ).head(10)

                for _, row in specialised.iterrows():
                    opt_r  = int(row["optical_rank"])
                    ir_r   = int(row["infrared_rank"])
                    rad_r  = int(row["radio_rank"])
                    spread = int(row["rank_spread"])

                    best   = row["best_type"]
                    emoji  = {
                        "Optical":  "🔭",
                        "Infrared": "🌡️",
                        "Radio":    "📡"
                    }.get(best, "🔭")

                    with st.expander(
                        f"{emoji} **{row['observatory']}** "
                        f"— Best for {best} · "
                        f"Rank spread: {spread} positions"
                    ):
                        c1, c2, c3 = st.columns(3)
                        c1.metric(
                            "🔭 Optical",
                            f"Rank #{opt_r}",
                            f"{row['optical_score']}/100 "
                            f"[{row['optical_grade']}]"
                        )
                        c2.metric(
                            "🌡️ Infrared",
                            f"Rank #{ir_r}",
                            f"{row['infrared_score']}/100 "
                            f"[{row['infrared_grade']}]"
                        )
                        c3.metric(
                            "📡 Radio",
                            f"Rank #{rad_r}",
                            f"{row['radio_score']}/100 "
                            f"[{row['radio_grade']}]"
                        )

                        # Why explanation
                        pwv    = row["pwv_mm"]
                        seeing = row["seeing_arcsec"]
                        jet    = row["jet_impact"]
                        alt    = row["altitude_m"]

                        reasons = []
                        if pwv and pwv < 2:
                            reasons.append(
                                f"very low PWV ({pwv}mm) "
                                f"— excellent for infrared")
                        if pwv and pwv > 10:
                            reasons.append(
                                f"high PWV ({pwv}mm) "
                                f"— poor for infrared/radio")
                        if seeing and seeing < 0.8:
                            reasons.append(
                                f"exceptional seeing "
                                f"({seeing}\") "
                                f"— ideal for optical")
                        if jet in ["Negligible", "Low"]:
                            reasons.append(
                                f"calm jet stream "
                                f"({jet}) "
                                f"— good for radio")
                        if jet in ["High", "Severe"]:
                            reasons.append(
                                f"strong jet stream "
                                f"({jet}) "
                                f"— hurts radio work")
                        if alt > 4000:
                            reasons.append(
                                f"very high altitude "
                                f"({alt}m) — less "
                                f"atmosphere above")

                        if reasons:
                            st.info(
                                "**Why this pattern:** "
                                + " · ".join(reasons))

                        st.caption(
                            f"{row['country']} · "
                            f"{alt}m · "
                            f"Seeing {seeing}\" · "
                            f"PWV {pwv}mm · "
                            f"Jet {jet}"
                        )

                st.markdown("---")

                # Full comparison table
                st.subheader("Full comparison table")
                cross_display = cross_df[[
                    "observatory", "country",
                    "altitude_m",
                    "optical_rank", "optical_score",
                    "optical_grade",
                    "infrared_rank", "infrared_score",
                    "infrared_grade",
                    "radio_rank", "radio_score",
                    "radio_grade",
                    "best_type", "rank_spread",
                    "pwv_mm", "seeing_arcsec",
                    "jet_impact"
                ]].rename(columns={
                    "observatory":     "Observatory",
                    "country":         "Country",
                    "altitude_m":      "Alt (m)",
                    "optical_rank":    "Opt Rank",
                    "optical_score":   "Opt Score",
                    "optical_grade":   "Opt Grade",
                    "infrared_rank":   "IR Rank",
                    "infrared_score":  "IR Score",
                    "infrared_grade":  "IR Grade",
                    "radio_rank":      "Radio Rank",
                    "radio_score":     "Radio Score",
                    "radio_grade":     "Radio Grade",
                    "best_type":       "Best For",
                    "rank_spread":     "Rank Spread",
                    "pwv_mm":          "PWV (mm)",
                    "seeing_arcsec":   "Seeing (\")",
                    "jet_impact":      "Jet Impact"
                })
                st.dataframe(
                    cross_display,
                    hide_index=True,
                    height=500
                )

                st.download_button(
                    label="Download cross-type "
                          "comparison as CSV",
                    data=cross_display.to_csv(
                        index=False),
                    file_name=f"cross_type_comparison_"
                              f"{utcnow().strftime('%Y-%m-%d')}"
                              f".csv",
                    mime="text/csv"
                )
        # ── What makes this different ─────────────────
        st.markdown("---")
        st.subheader("💡 Why efficiency score matters")
        st.markdown(f"""
A site with a perfect **100/100 weather score** but
only **3 dark hours** is less useful than a site with
**85/100 weather** and **10 dark hours**.

The efficiency score captures this by combining:

- **How good the weather is** — cloud, humidity, wind
- **How many hours of darkness are available** tonight
- **How much of the dark time is moon-free**
- **How sharp the images will be** — atmospheric seeing
- **{'PWV for infrared transmission' if tel_type == 'Infrared' else 'Jet stream impact on upper atmosphere' if tel_type == 'Radio' else 'Overall atmospheric stability'}**

The **usable hours** estimate tells you exactly how many
hours of high-quality science you can realistically
expect from each site tonight — the number telescope
schedulers actually care about.
        """)

# ═══════════════════════════════════════════════════════
# TAB 12 — SNR Calculator
# ═══════════════════════════════════════════════════════
with tab12:
    st.subheader("📡 Signal-to-Noise Ratio Calculator")
    st.caption(
        "Calculate how detectable your target object will be "
        "tonight at each observatory. Shows full noise budget "
        "breakdown — shot noise, sky background, dark current, "
        "read noise and scintillation. "
        "Accuracy: ~75% for point sources."
    )

    st.markdown("---")

    # ── Controls ──────────────────────────────────────────
    snr_col1, snr_col2, snr_col3 = st.columns(3)

    with snr_col1:
        # Object selector
        snr_obj_type = st.selectbox(
            "Object type",
            ["All", "Planets", "Messier Objects",
             "NGC Objects", "Famous Stars"],
            key="snr_obj_type"
        )

        # Filter objects that have magnitudes
        if snr_obj_type == "Planets":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if k in ["Mercury", "Venus",
                                "Mars", "Jupiter",
                                "Saturn", "Uranus",
                                "Neptune"]]
        elif snr_obj_type == "Messier Objects":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if k.startswith("M")]
        elif snr_obj_type == "NGC Objects":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if k.startswith("NGC")]
        elif snr_obj_type == "Famous Stars":
            obj_keys = [k for k in OBJECT_MAGNITUDES
                       if not k.startswith(("M", "N",
                           "Mercury", "Venus", "Mars",
                           "Jupiter", "Saturn",
                           "Uranus", "Neptune"))]
        else:
            obj_keys = list(OBJECT_MAGNITUDES.keys())

        snr_object = st.selectbox(
            "Select target object",
            obj_keys,
            key="snr_object"
        )

    with snr_col2:
        # Custom magnitude option
        use_custom_mag = st.toggle(
            "Use custom magnitude",
            value=False,
            key="custom_mag_toggle"
        )
        if use_custom_mag:
            object_mag = st.number_input(
                "Object magnitude",
                min_value=-5.0,
                max_value=25.0,
                value=float(OBJECT_MAGNITUDES.get(
                    snr_object, 8.0)),
                step=0.1,
                key="custom_mag"
            )
        else:
            object_mag = OBJECT_MAGNITUDES.get(
                snr_object, 8.0)
            st.metric(
                "Object magnitude",
                f"{object_mag} mag"
            )

        # Exposure time
        exposure_preset = st.selectbox(
            "Exposure time",
            ["30 seconds", "1 minute", "5 minutes",
             "10 minutes", "30 minutes", "1 hour",
             "2 hours", "Custom"],
            index=2,
            key="exp_preset"
        )

        preset_map = {
            "30 seconds": 30,
            "1 minute":   60,
            "5 minutes":  300,
            "10 minutes": 600,
            "30 minutes": 1800,
            "1 hour":     3600,
            "2 hours":    7200,
        }

        if exposure_preset == "Custom":
            exposure_s = st.number_input(
                "Custom exposure (seconds)",
                min_value=1,
                max_value=36000,
                value=300,
                key="custom_exp"
            )
        else:
            exposure_s = preset_map[exposure_preset]

    with snr_col3:
        # Moon conditions
        st.markdown("**Moon conditions**")
        moon_phase_input = st.slider(
            "Moon illumination %",
            0, 100, 27,
            key="snr_moon_phase"
        )
        moon_alt_input = st.slider(
            "Moon altitude °",
            -90, 90, 20,
            key="snr_moon_alt"
        )

        sky_brightness = get_sky_brightness(
            moon_phase_input, moon_alt_input)
        st.metric(
            "Sky brightness",
            f"{sky_brightness} mag/arcsec²",
            help="Higher = darker sky = better"
        )

    st.markdown("---")

    # ── Single observatory deep dive ──────────────────────
    st.subheader("Single observatory analysis")

    snr_obs = st.selectbox(
        "Select observatory",
        df["observatory"].tolist(),
        key="snr_obs"
    )

    obs_row   = df[df["observatory"] == snr_obs].iloc[0]
    tel_specs = TELESCOPE_SPECS.get(
        snr_obs, TELESCOPE_SPECS["default"])

    # Get seeing for this observatory
    atm_data = load_atmospheric_cached()
    obs_atm  = atm_data[
        atm_data["observatory"] == snr_obs]
    seeing   = (obs_atm.iloc[0]["seeing_arcsec"]
                if not obs_atm.empty else 1.5)
    pwv      = (obs_atm.iloc[0]["pwv_mm"]
                if not obs_atm.empty else None)

    # Force recalculation when inputs change
    obs_row    = df[df["observatory"] == snr_obs].iloc[0]
    tel_specs  = TELESCOPE_SPECS.get(
        snr_obs, TELESCOPE_SPECS["default"])
    atm_data   = load_atmospheric_cached()
    obs_atm    = atm_data[
        atm_data["observatory"] == snr_obs]
    seeing     = (obs_atm.iloc[0]["seeing_arcsec"]
              if not obs_atm.empty else 1.5) or 1.5
    pwv        = (obs_atm.iloc[0]["pwv_mm"]
              if not obs_atm.empty else None)

    # Force fresh calculation every time
    obs_row    = df[df["observatory"] == snr_obs].iloc[0]
    tel_specs  = TELESCOPE_SPECS.get(
        snr_obs, TELESCOPE_SPECS["default"])
    atm_data   = load_atmospheric_cached()
    obs_atm    = atm_data[
        atm_data["observatory"] == snr_obs]

    if not obs_atm.empty:
        seeing_val = obs_atm.iloc[0].get("seeing_arcsec")
        pwv_val    = obs_atm.iloc[0].get("pwv_mm")
        seeing     = float(seeing_val) if seeing_val else 1.5
        pwv        = float(pwv_val) if pwv_val else None
    else:
        seeing = 1.5
        pwv    = None

    # Debug display - remove later
    st.caption(
        f"DEBUG: obj={snr_object}, mag={object_mag}, "
        f"obs={snr_obs}, exp={exposure_s}s, "
        f"seeing={seeing}, sky={sky_brightness}"
    )

    result = calculate_snr(
        object_magnitude      = float(object_mag),
        exposure_time_s       = int(exposure_s),
        telescope_specs       = tel_specs,
        sky_brightness_mag    = float(sky_brightness),
        seeing_arcsec         = float(seeing),
        object_name           = snr_object,
        object_altitude_deg   = None,
        pwv_mm                = pwv
    )

    # SNR display
    snr_val = result["snr"]
    if snr_val >= 50:   snr_color = "#1D9E75"
    elif snr_val >= 10: snr_color = "#378ADD"
    elif snr_val >= 5:  snr_color = "#EF9F27"
    else:               snr_color = "#E24B4A"

    st.markdown(
        f"<div style='background:{snr_color}22;"
        f"border:1px solid {snr_color};"
        f"border-radius:8px;padding:16px;"
        f"text-align:center;margin:16px 0'>"
        f"<div style='font-size:48px;"
        f"font-weight:bold;color:{snr_color}'>"
        f"SNR = {snr_val}</div>"
        f"<div style='font-size:16px;"
        f"color:{snr_color}'>"
        f"{result['snr_quality']}</div>"
        f"<div style='font-size:12px;color:#888;"
        f"margin-top:4px'>"
        f"{snr_object} · {snr_obs} · "
        f"{exposure_preset if exposure_preset != 'Custom' else f'{exposure_s}s'}"
        f"</div></div>",
        unsafe_allow_html=True
    )

    # Key metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("SNR",           snr_val)
    m2.metric("Limiting mag",
              result["limiting_magnitude"])
    m3.metric("Telescope",
              tel_specs.get("name",
              f"{tel_specs['aperture_m']}m"))
    m4.metric("Seeing",        f"{seeing}\"")
    m5.metric("Sky brightness",
              f"{sky_brightness} mag/arcsec²")

    # Exposure times for SNR targets
    st.markdown("**Time needed to reach SNR targets**")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("SNR = 5  (detection)",
              result["time_for_snr5"])
    t2.metric("SNR = 10 (clear detection)",
              result["time_for_snr10"])
    t3.metric("SNR = 50 (science quality)",
              result["time_for_snr50"])
    t4.metric("SNR = 100 (publication)",
              result["time_for_snr100"])

    # Noise budget chart
    st.markdown("**Noise budget breakdown**")
    budget = result["noise_budget"]

    import matplotlib.pyplot as plt
    import io

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12, 4))

    # Bar chart
    sources = list(budget.keys())
    values  = list(budget.values())
    colors  = ["#1D9E75", "#378ADD", "#EF9F27",
                "#E24B4A", "#AFA9EC"]

    bars = ax1.barh(sources, values,
                    color=colors[:len(sources)],
                    height=0.6)
    for bar, val in zip(bars, values):
        ax1.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}e⁻",
            va="center", fontsize=9, color="white"
        )
    ax1.set_xlabel("Noise (electrons)",
                   color="white", fontsize=9)
    ax1.set_title("Noise sources",
                  color="white", fontsize=11,
                  fontweight="bold")
    ax1.set_facecolor("#0E1117")
    ax1.tick_params(colors="white", labelsize=9)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_color("#444441")
    ax1.spines["bottom"].set_color("#444441")

    # Pie chart
    non_zero = [(s, v) for s, v in
                zip(sources, values) if v > 0]
    if non_zero:
        pie_sources = [x[0] for x in non_zero]
        pie_values  = [x[1] for x in non_zero]
        ax2.pie(
            pie_values,
            labels=pie_sources,
            colors=colors[:len(pie_sources)],
            autopct="%1.1f%%",
            textprops={"color": "white",
                       "fontsize": 9}
        )
        ax2.set_title("Noise distribution",
                      color="white", fontsize=11,
                      fontweight="bold")

    fig.patch.set_facecolor("#0E1117")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150,
                facecolor="#0E1117",
                bbox_inches="tight")
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()
    st.image(img_data, width='stretch')
    plt.close()

    st.markdown("---")

    # ── Compare across observatories ──────────────────────
    st.subheader(
        "SNR comparison across all observatories")
    st.caption(
        "Which observatory gives the best SNR "
        "for your target tonight?"
    )

    with st.spinner(
        "Calculating SNR for all observatories..."
    ):
        all_snr = get_snr_for_all_observatories(
            object_name      = snr_object,
            object_magnitude = object_mag,
            exposure_time_s  = exposure_s,
            observatories_df = df,
            moon_phase_pct   = moon_phase_input,
            moon_altitude_deg = moon_alt_input,
            seeing_data      = atm_data,
            pwv_data         = atm_data
        )

    if not all_snr.empty:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Best observatory",
                  all_snr.iloc[0]["observatory"].replace(
                      " Observatory", "")[:20])
        s2.metric("Best SNR",
                  all_snr.iloc[0]["snr"])
        s3.metric("Best telescope",
                  all_snr.iloc[0]["telescope"])
        s4.metric("Best aperture",
                  f"{all_snr.iloc[0]['aperture_m']}m")

        st.markdown("**Top 10 observatories by SNR**")
        for _, row in all_snr.head(10).iterrows():
            snr_v = row["snr"]
            if snr_v >= 50:   ec = "#1D9E75"
            elif snr_v >= 10: ec = "#378ADD"
            elif snr_v >= 5:  ec = "#EF9F27"
            else:             ec = "#E24B4A"

            with st.expander(
                f"**{row['observatory']}** — "
                f"SNR {snr_v} · "
                f"{row['snr_quality']} · "
                f"{row['telescope']}"
            ):
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("SNR",       snr_v)
                c2.metric("Aperture",
                          f"{row['aperture_m']}m")
                c3.metric("Limit mag",
                          row["limiting_mag"])
                c4.metric("Time for SNR 10",
                          row["time_snr10"])
                c5.metric("Time for SNR 50",
                          row["time_snr50"])
                st.caption(
                    f"{row['country']} · "
                    f"Seeing {row['seeing']}\" · "
                    f"Sky {row['sky_brightness']} "
                    f"mag/arcsec²"
                )

        # Full table
        st.markdown("**Full SNR table**")
        snr_display = all_snr[[
            "observatory", "country", "telescope",
            "aperture_m", "snr", "snr_quality",
            "limiting_mag", "time_snr5",
            "time_snr10", "time_snr50"
        ]].rename(columns={
            "observatory":  "Observatory",
            "country":      "Country",
            "telescope":    "Telescope",
            "aperture_m":   "Aperture (m)",
            "snr":          "SNR",
            "snr_quality":  "Quality",
            "limiting_mag": "Limit Mag",
            "time_snr5":    "Time SNR=5",
            "time_snr10":   "Time SNR=10",
            "time_snr50":   "Time SNR=50"
        })
        st.dataframe(snr_display,
                     hide_index=True, height=500)

        st.download_button(
            label="Download SNR comparison as CSV",
            data=snr_display.to_csv(index=False),
            file_name=f"snr_{snr_object.replace(' ', '_')}_"
                      f"{utcnow().strftime('%Y-%m-%d')}"
                      f".csv",
            mime="text/csv"
        )

    st.markdown("---")
    st.caption(
        "⚠️ SNR estimates are approximate (~75% accuracy "
        "for point sources). For precise exposure times "
        "use the official ETC for your telescope. "
        "Extended objects (galaxies, nebulae) may be "
        "overestimated by 2-10x."
    )

# ═══════════════════════════════════════════════════════
# TAB 13 — Live Sky Chart
# ═══════════════════════════════════════════════════════
with tab13:
    st.subheader("🌌 Live Sky Chart")
    st.caption(
        "Real-time sky view for any observatory. "
        "Shows stars, planets, Moon and your target "
        "object. Calculated fresh for the current moment."
    )

    # Controls
    sky_col1, sky_col2 = st.columns([2, 1])
    with sky_col1:
        sky_obs = st.selectbox(
            "Select observatory",
            df["observatory"].tolist(),
            key="sky_obs"
        )
    with sky_col2:
        show_target = st.toggle(
            "Show target object",
            value=False,
            key="sky_show_target"
        )

    sky_target = None
    if show_target:
        from object_visibility import OBJECTS
        sky_target = st.selectbox(
            "Target object",
            list(OBJECTS.keys()),
            key="sky_target"
        )

    sky_row = df[
        df["observatory"] == sky_obs].iloc[0]

    with st.spinner(
        f"Computing live sky for {sky_obs}..."
    ):
        sky = compute_sky(
            float(sky_row["latitude"]),
            float(sky_row["longitude"]),
            object_name=sky_target
        )

    # ── Sky state banner ──────────────────────────────────
    state_colors = {
        "day":      "#1a3a5c",
        "civil":    "#0d1b2a",
        "twilight": "#050d1a",
        "night":    "#010408"
    }
    state_labels = {
        "day":      "☀️ Daytime — stars not visible",
        "civil":    "🌆 Civil twilight",
        "twilight": "🌃 Astronomical twilight",
        "night":    "🌑 Astronomical night — full dark"
    }
    sky_state = sky["sky_state"]
    # Quick Google Earth link
    gearth_sky = (
        f"https://earth.google.com/web/@"
        f"{sky_row['latitude']},{sky_row['longitude']},"
        f"{sky_row['altitude_m']}a,5000d,35y,0h,0t,0r"
)
    st.caption(
        f"📍 {sky_obs} · "
        f"[Open in Google Earth →]({gearth_sky})"
)
    st.markdown(
        f"<div style='background:{state_colors[sky_state]};"
        f"border-radius:8px;padding:8px 16px;"
        f"margin-bottom:8px;text-align:center;"
        f"color:white;font-weight:bold'>"
        f"{state_labels[sky_state]} · "
        f"Sun altitude: {sky['sun']['altitude']}° · "
        f"Computed: {sky['computed_at']}"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Draw sky chart ────────────────────────────────────
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    import io

    fig = plt.figure(
        figsize=(10, 10),
        facecolor=sky["sky_color"]
    )
    ax  = fig.add_subplot(
        111, projection="polar",
        facecolor=sky["sky_color"]
    )

    # Grid
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.33, 0.67, 1.0])
    ax.set_yticklabels(
        ["Zenith", "60°", "30°", "Horizon"],
        color="#444", fontsize=7
    )
    ax.grid(
        color="#111", alpha=0.3,
        linewidth=0.5, linestyle="--"
    )

    # Cardinal directions
    ax.set_xticks([0, math.pi/2, math.pi, 3*math.pi/2])
    ax.set_xticklabels(
        ["N", "E", "S", "W"],
        color="white", fontsize=14,
        fontweight="bold"
    )

    # Horizon circle
    theta_circle = np.linspace(0, 2*math.pi, 100)
    ax.plot(
        theta_circle,
        [1.0] * 100,
        color="#2a4a2a",
        linewidth=2,
        alpha=0.8
    )

    # ── Constellation lines ───────────────────────────────
    for line in sky["constellation_lines"]:
        ax.plot(
            [line["t1"], line["t2"]],
            [line["r1"], line["r2"]],
            color="#1a3a5c",
            linewidth=0.8,
            alpha=0.6,
            zorder=1
        )

    # ── Stars ─────────────────────────────────────────────
    for star in sky["stars"]:
        if not star["visible"]:
            continue
        color   = "white"
        opacity = star["opacity"]
        size    = star["size"] ** 2

        ax.scatter(
            star["theta"], star["r"],
            s=size,
            c=color,
            alpha=opacity,
            zorder=3,
            edgecolors="none"
        )

        # Label only brightest
        if star["magnitude"] < 1.5:
            ax.annotate(
                star["name"],
                (star["theta"], star["r"]),
                xytext=(5, 5),
                textcoords="offset points",
                color="lightgray",
                fontsize=7,
                zorder=4
            )

    # ── Planets ───────────────────────────────────────────
    for planet in sky["planets"]:
        if not planet["visible"]:
            continue
        ax.scatter(
            planet["theta"], planet["r"],
            s=planet["size"] ** 2,
            c=planet["color"],
            alpha=0.9,
            zorder=5,
            edgecolors="white",
            linewidths=0.5
        )
        ax.annotate(
            planet["name"],
            (planet["theta"], planet["r"]),
            xytext=(6, 6),
            textcoords="offset points",
            color=planet["color"],
            fontsize=8,
            fontweight="bold",
            zorder=6
        )

    # ── Moon ──────────────────────────────────────────────
    moon = sky["moon"]
    if moon["visible"]:
        ax.scatter(
            moon["theta"], moon["r"],
            s=300,
            c="#FFFACD",
            alpha=0.95,
            zorder=7,
            edgecolors="#FFD700",
            linewidths=1
        )
        ax.annotate(
            f"Moon\n{moon['phase']:.0f}%",
            (moon["theta"], moon["r"]),
            xytext=(8, 8),
            textcoords="offset points",
            color="#FFFACD",
            fontsize=8,
            fontweight="bold",
            zorder=8
        )

    # ── Sun ───────────────────────────────────────────────
    sun = sky["sun"]
    if sun["visible"]:
        ax.scatter(
            sun["theta"], sun["r"],
            s=500,
            c="#FFD700",
            alpha=0.95,
            zorder=7,
            edgecolors="#FF8C00",
            linewidths=2
        )
        ax.annotate(
            "Sun",
            (sun["theta"], sun["r"]),
            xytext=(8, 8),
            textcoords="offset points",
            color="#FFD700",
            fontsize=9,
            fontweight="bold",
            zorder=8
        )

    # ── Target object ─────────────────────────────────────
    if sky.get("target"):
        target = sky["target"]
        if target["visible"]:
            ax.scatter(
                target["theta"], target["r"],
                s=400,
                c="none",
                alpha=1.0,
                zorder=9,
                edgecolors="#FF0040",
                linewidths=2,
                marker="o"
            )
            ax.scatter(
                target["theta"], target["r"],
                s=50,
                c="#FF0040",
                alpha=0.9,
                zorder=10
            )
            ax.annotate(
                f"► {target['name']}\n"
                f"Alt: {target['altitude']}°",
                (target["theta"], target["r"]),
                xytext=(10, 10),
                textcoords="offset points",
                color="#FF0040",
                fontsize=9,
                fontweight="bold",
                zorder=11,
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="#000",
                    alpha=0.7,
                    edgecolor="#FF0040"
                )
            )
        else:
            st.warning(
                f"{sky_target} is currently below "
                f"the horizon at {sky_obs}."
            )

    # Title
    ax.set_title(
        f"{sky_obs}\n"
        f"Lat {sky['lat']:.1f}° · "
        f"Lon {sky['lon']:.1f}° · "
        f"{sky['computed_at']}",
        color="white",
        fontsize=10,
        fontweight="bold",
        pad=20
    )

    # Legend
    legend_items = [
        plt.scatter([], [], s=80,
                    c="white", label="Stars"),
        plt.scatter([], [], s=150,
                    c="#FAD5A5",
                    edgecolors="white",
                    label="Planets"),
        plt.scatter([], [], s=200,
                    c="#FFFACD",
                    edgecolors="#FFD700",
                    label="Moon"),
    ]
    if sky.get("target") and sky["target"]["visible"]:
        legend_items.append(
            plt.scatter([], [], s=150,
                        c="none",
                        edgecolors="#FF0040",
                        linewidths=2,
                        label="Target object")
        )
    ax.legend(
        handles=legend_items,
        loc="lower left",
        fontsize=8,
        facecolor="#0A0A1A",
        labelcolor="white",
        framealpha=0.8
    )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(
        buf, format="png", dpi=150,
        facecolor=sky["sky_color"],
        bbox_inches="tight"
    )
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()
    st.image(img_data, width='stretch')
    plt.close()

    # ── Object positions table ────────────────────────────
    st.markdown("---")
    st.subheader("Object positions right now")

    visible_objects = []

    for planet in sky["planets"]:
        visible_objects.append({
            "Object":    planet["name"],
            "Type":      "Planet",
            "Altitude":  f"{planet['altitude']}°",
            "Azimuth":   f"{planet['azimuth']}°",
            "Magnitude": planet["magnitude"],
            "Visible":   "✅" if planet["visible"]
                         else "❌ Below horizon"
        })

    for star in sky["stars"]:
        if star["magnitude"] < 2.0:
            visible_objects.append({
                "Object":    star["name"],
                "Type":      "Star",
                "Altitude":  f"{star['altitude']}°",
                "Azimuth":   f"{star['azimuth']}°",
                "Magnitude": star["magnitude"],
                "Visible":   "✅" if star["visible"]
                             else "❌ Below horizon"
            })

    moon = sky["moon"]
    visible_objects.append({
        "Object":    "Moon",
        "Type":      f"Moon ({moon['phase']:.0f}%)",
        "Altitude":  f"{moon['altitude']}°",
        "Azimuth":   f"{moon['azimuth']}°",
        "Magnitude": -12.7,
        "Visible":   "✅" if moon["visible"]
                     else "❌ Below horizon"
    })

    import pandas as pd
    obj_df = pd.DataFrame(visible_objects)
    st.dataframe(obj_df, hide_index=True, height=400)

    st.caption(
        "Chart updates each time you select a new "
        "observatory. All positions calculated live "
        "using PyEphem for the current UTC time."
    )

# ═══════════════════════════════════════════════════════
# TAB 14 — 7-Day Forecast
# ═══════════════════════════════════════════════════════
with tab14:
    st.subheader("📅 7-Day Observation Forecast")
    st.caption(
        "7-day weather forecast for any observatory. "
        "Shows predicted observation quality scores, "
        "best observing hour each night, cloud cover, "
        "humidity and wind. Updated every hour."
    )

    fc_obs = st.selectbox(
        "Select observatory",
        df["observatory"].tolist(),
        key="fc_obs"
    )
    fc_row = df[df["observatory"] == fc_obs].iloc[0]

    gearth_fc = (
        f"https://earth.google.com/web/@"
        f"{fc_row['latitude']},{fc_row['longitude']},"
        f"{fc_row['altitude_m']}a,5000d,35y,0h,0t,0r"
)
    st.caption(
        f"📍 {fc_obs} · "
        f"[Open location in Google Earth →]({gearth_fc})"
)
    fc_row = df[df["observatory"] == fc_obs].iloc[0]

    with st.spinner(
        f"Fetching 7-day forecast for {fc_obs}..."
    ):
        fc_df    = fetch_forecast(
            float(fc_row["latitude"]),
            float(fc_row["longitude"]),
            days=7
        )
        daily_df = get_daily_summary(fc_df)

    if daily_df.empty:
        st.error("Could not fetch forecast data.")
    else:
        # ── Summary cards ─────────────────────────────────
        st.subheader("Week at a glance")
        cols = st.columns(len(daily_df))
        for i, (_, row) in enumerate(
            daily_df.iterrows()
        ):
            with cols[i]:
                score = row["night_score"]
                if score >= 80:
                    color = "#1D9E75"
                    emoji = "🟢"
                elif score >= 60:
                    color = "#378ADD"
                    emoji = "🔵"
                elif score >= 40:
                    color = "#EF9F27"
                    emoji = "🟡"
                else:
                    color = "#E24B4A"
                    emoji = "🔴"

                st.markdown(
                    f"<div style='background:{color}22;"
                    f"border:1px solid {color};"
                    f"border-radius:8px;"
                    f"padding:8px;text-align:center'>"
                    f"<div style='font-size:11px;"
                    f"color:#888'>{row['day_name']}</div>"
                    f"<div style='font-size:13px;"
                    f"color:white;font-weight:bold'>"
                    f"{row['date_display']}</div>"
                    f"<div style='font-size:24px;"
                    f"font-weight:bold;color:{color}'>"
                    f"{score}</div>"
                    f"<div style='font-size:10px;"
                    f"color:{color}'>"
                    f"{row['condition']}</div>"
                    f"<div style='font-size:10px;"
                    f"color:#888'>☁️{row['avg_cloud']}%"
                    f" 💧{row['avg_humidity']}%</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # ── 7-day score chart ──────────────────────────────
        st.subheader("Observation score forecast")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import io

        fig, ax = plt.subplots(figsize=(12, 4))
        dates   = daily_df["date_display"].tolist()
        scores  = daily_df["night_score"].tolist()
        colors  = []
        for s in scores:
            if s >= 80:   colors.append("#1D9E75")
            elif s >= 60: colors.append("#378ADD")
            elif s >= 40: colors.append("#EF9F27")
            else:         colors.append("#E24B4A")

        bars = ax.bar(dates, scores,
                      color=colors, width=0.6)

        for bar, score in zip(bars, scores):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{score}",
                ha="center", va="bottom",
                color="white", fontsize=10,
                fontweight="bold"
            )

        ax.axhline(y=80, color="#1D9E75",
                   linestyle="--", alpha=0.4,
                   linewidth=1, label="Excellent")
        ax.axhline(y=60, color="#378ADD",
                   linestyle="--", alpha=0.4,
                   linewidth=1, label="Good")
        ax.set_ylim(0, 115)
        ax.set_ylabel("Night Score", color="white")
        ax.set_title(
            f"7-Day Forecast — {fc_obs}",
            color="white", fontsize=12,
            fontweight="bold"
        )
        ax.set_facecolor("#0E1117")
        fig.patch.set_facecolor("#0E1117")
        ax.tick_params(colors="white")
        ax.yaxis.label.set_color("white")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#444441")
        ax.spines["bottom"].set_color("#444441")

        legend_items = [
            mpatches.Patch(
                color="#1D9E75", label="Excellent (80+)"),
            mpatches.Patch(
                color="#378ADD", label="Good (60-79)"),
            mpatches.Patch(
                color="#EF9F27", label="Marginal (40-59)"),
            mpatches.Patch(
                color="#E24B4A", label="Poor (<40)")
        ]
        ax.legend(
            handles=legend_items, loc="upper right",
            fontsize=8, facecolor="#0E1117",
            labelcolor="white"
        )

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=150,
                    facecolor="#0E1117",
                    bbox_inches="tight")
        buf.seek(0)
        img_data = buf.getvalue()
        buf.close()
        st.image(img_data, width='stretch')
        plt.close()

        st.markdown("---")

        # ── Daily detail expanders ─────────────────────────
        st.subheader("Day by day detail")
        for _, row in daily_df.iterrows():
            score = row["night_score"]
            if score >= 80:   emoji = "🟢"
            elif score >= 60: emoji = "🔵"
            elif score >= 40: emoji = "🟡"
            else:             emoji = "🔴"

            with st.expander(
                f"{emoji} **{row['day_name']} "
                f"{row['date_display']}** — "
                f"Night score: {score}/100 "
                f"[{row['condition']}] · "
                f"Best hour: {row['best_hour']}"
            ):
                d1, d2, d3, d4, d5 = st.columns(5)
                d1.metric("Night Score",
                          f"{row['night_score']}/100")
                d2.metric("Best Hour",
                          row["best_hour"])
                d3.metric("Avg Cloud",
                          f"{row['avg_cloud']}%")
                d4.metric("Avg Humidity",
                          f"{row['avg_humidity']}%")
                d5.metric("Avg Wind",
                          f"{row['avg_wind']} m/s")

                t1, t2, t3 = st.columns(3)
                t1.metric("Min Temp",
                          f"{row['min_temp']}°C")
                t2.metric("Max Temp",
                          f"{row['max_temp']}°C")
                t3.metric("Rain Probability",
                          f"{row['precip_prob']}%")

                # Hourly chart for this day
                hourly = row["hourly_scores"]
                if hourly:
                    hours  = [h["hour"]
                               for h in hourly]
                    scores_h = [h["score"]
                                 for h in hourly]
                    h_colors = []
                    for s in scores_h:
                        if s >= 80:
                            h_colors.append("#1D9E75")
                        elif s >= 60:
                            h_colors.append("#378ADD")
                        elif s >= 40:
                            h_colors.append("#EF9F27")
                        elif s > 0:
                            h_colors.append("#E24B4A")
                        else:
                            h_colors.append("#444441")

                    fig2, ax2 = plt.subplots(
                        figsize=(10, 2))
                    ax2.bar(hours, scores_h,
                            color=h_colors, width=0.8)
                    ax2.set_xticks(range(0, 24, 3))
                    ax2.set_xticklabels(
                        [f"{h:02d}:00"
                         for h in range(0, 24, 3)],
                        fontsize=7, color="white"
                    )
                    ax2.set_ylim(0, 105)
                    ax2.set_ylabel("Score",
                                   fontsize=8,
                                   color="white")
                    ax2.set_facecolor("#0E1117")
                    fig2.patch.set_facecolor("#0E1117")
                    ax2.tick_params(colors="white")
                    ax2.spines["top"].set_visible(False)
                    ax2.spines["right"].set_visible(False)
                    ax2.spines["left"].set_color(
                        "#444441")
                    ax2.spines["bottom"].set_color(
                        "#444441")

                    buf2 = io.BytesIO()
                    plt.tight_layout()
                    plt.savefig(
                        buf2, format="png", dpi=100,
                        facecolor="#0E1117",
                        bbox_inches="tight"
                    )
                    buf2.seek(0)
                    st.image(buf2.getvalue(), width='stretch')
                    plt.close()

        st.markdown("---")

        # ── Full forecast table ────────────────────────────
        st.subheader("Full forecast table")
        fc_display = daily_df[[
            "date", "day_name", "night_score",
            "condition", "best_hour", "best_score",
            "avg_cloud", "avg_humidity", "avg_wind",
            "min_temp", "max_temp", "precip_prob"
        ]].rename(columns={
            "date":         "Date",
            "day_name":     "Day",
            "night_score":  "Night Score",
            "condition":    "Condition",
            "best_hour":    "Best Hour",
            "best_score":   "Best Score",
            "avg_cloud":    "Cloud %",
            "avg_humidity": "Humidity %",
            "avg_wind":     "Wind m/s",
            "min_temp":     "Min °C",
            "max_temp":     "Max °C",
            "precip_prob":  "Rain Prob %"
        })
        st.dataframe(fc_display,
                     hide_index=True, height=300)

        st.download_button(
            label="Download forecast as CSV",
            data=fc_display.to_csv(index=False),
            file_name=f"forecast_{fc_obs.replace(' ', '_')}_"
                      f"{utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

        st.caption(
            "Forecast data from Open-Meteo · "
            "Free, open-source weather API · "
            "Night scores based on 18:00-06:00 UTC hours · "
            "Updated hourly"
        )

# ═══════════════════════════════════════════════════════
# TAB 15 — Comet Tracker
# ═══════════════════════════════════════════════════════
with tab15:
    st.subheader("☄️ Comet Tracker")
    st.caption(
        "Track currently observable comets worldwide. "
        "Shows real-time visibility from your selected "
        "observatory, brightness, and which telescope "
        "is needed to see each comet tonight."
    )

    comets = get_current_comets()

    # Summary metrics
    trackable = [c for c in comets
                 if c.get("ra_deg") is not None]
    naked_eye = [c for c in comets
                 if c.get("magnitude", 99) < 6
                 and c.get("ra_deg") is not None]
    bino      = [c for c in comets
                 if 6 <= c.get("magnitude", 99) < 10
                 and c.get("ra_deg") is not None]

    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.metric("Total Comets",      len(comets))
    cm2.metric("Trackable Tonight", len(trackable))
    cm3.metric("Naked Eye",         len(naked_eye))
    cm4.metric("Binoculars",        len(bino))

    st.markdown("---")

    # Observatory selector
    comet_obs = st.selectbox(
        "Select observatory for visibility",
        df["observatory"].tolist(),
        key="comet_obs"
    )
    comet_row = df[
        df["observatory"] == comet_obs].iloc[0]
    clat = float(comet_row["latitude"])
    clon = float(comet_row["longitude"])

    st.markdown("---")

    # Display each comet
    st.subheader(
        f"Comet visibility from {comet_obs}")

    for comet in comets:
        mag     = comet.get("magnitude", 99)
        status  = comet.get("status", "Unknown")

        if "🟢" in status:   status_emoji = "🟢"
        elif "🟡" in status: status_emoji = "🟡"
        elif "🔴" in status: status_emoji = "🔴"
        else:                status_emoji = "⚪"

        # Get visibility
        vis = get_comet_visibility(
            comet, clat, clon)

        vis_str = ""
        if vis:
            if vis["visible"]:
                vis_str = (f"🔭 Visible — "
                           f"Alt {vis['altitude']}°")
            else:
                vis_str = (f"❌ Below horizon — "
                           f"Alt {vis['altitude']}°")
        else:
            vis_str = "📍 No position data"

        with st.expander(
            f"{status_emoji} **{comet['name']}** — "
            f"Magnitude {mag} · "
            f"{magnitude_to_visibility(mag)} · "
            f"{vis_str}"
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Magnitude",   mag)
            c2.metric("Type",        comet["type"])
            c3.metric("Perihelion",
                      comet.get("perihelion", "N/A"))
            c4.metric("Discovered",
                      str(comet.get(
                          "discovery_year", "N/A")))

            if vis:
                v1, v2, v3, v4 = st.columns(4)
                v1.metric("Altitude",
                          f"{vis['altitude']}°")
                v2.metric("Azimuth",
                          f"{vis['azimuth']}°")
                v3.metric("Rises",
                          vis.get("rise_time", "N/A"))
                v4.metric("Sets",
                          vis.get("set_time", "N/A"))

            st.info(
                f"**{comet['name']}** — "
                f"{comet.get('notes', '')} · "
                f"Discovered by "
                f"{comet.get('discoverer', 'Unknown')} · "
                f"Type: {comet_type_info(comet['type'])}"
            )

            if comet.get("period_yr"):
                st.caption(
                    f"Orbital period: "
                    f"{comet['period_yr']} years"
                )

    st.markdown("---")

    # World map showing which observatories
    # can see comets tonight
    st.subheader(
        "World map — comet visibility tonight")
    st.caption(
        "Green markers can see at least one comet "
        "above 10° altitude right now."
    )

    import folium
    m_comet = folium.Map(
        location=[20, 0], zoom_start=2,
        tiles="CartoDB positron"
    )

    # Sample every 5th observatory for speed
    sample_df = df.iloc[::5]

    for _, obs_row in sample_df.iterrows():
        lat = float(obs_row["latitude"])
        lon = float(obs_row["longitude"])

        visible_comets = []
        for comet in trackable:
            vis = get_comet_visibility(
                comet, lat, lon)
            if vis and vis["visible"]:
                visible_comets.append(
                    comet["name"])

        color   = "#1D9E75" if visible_comets else "#444441"
        tooltip = (
            f"{obs_row['observatory']} — "
            f"{len(visible_comets)} comets visible"
            if visible_comets
            else f"{obs_row['observatory']} — no comets"
        )
        popup = (
            f"<b>{obs_row['observatory']}</b><br>"
            f"Visible comets:<br>" +
            "<br>".join(visible_comets)
            if visible_comets
            else f"<b>{obs_row['observatory']}</b><br>"
                 f"No comets above horizon"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=tooltip,
            popup=folium.Popup(popup, max_width=200)
        ).add_to(m_comet)

    st_folium(m_comet, width=None, height=400)

    st.markdown("---")

    # Educational section
    st.subheader("🎓 About comets")
    st.markdown("""
**What is a comet?**
A comet is an icy body from the outer solar system.
When it approaches the Sun, heat vaporises the ice
creating a glowing coma and tail that can stretch
millions of kilometres.

**Types of comets:**
- **Short-period** — orbit the Sun in under 200 years.
  Predictable and well-studied. Example: Halley's Comet.
- **Long-period** — take thousands of years per orbit.
  Often first-time visitors from the Oort Cloud.
- **Interstellar** — from outside our solar system entirely.
  Only 3 confirmed: 1I/Oumuamua, 2I/Borisov, 3I/ATLAS.
- **Sungrazers** — pass extremely close to the Sun.
  Often spectacular but frequently break apart.

**Why are comets unpredictable?**
Comets are nicknamed "dirty snowballs". As they heat up
they outgas jets of material that can change their
brightness dramatically. A comet predicted at magnitude 8
can brighten to magnitude 1 — or completely disintegrate.

**How to observe:**
- Start with binoculars — sweep slowly across the
  predicted position
- Look for a fuzzy patch that does not look like a star
- The tail always points away from the Sun
- Best viewing is away from city lights
    """)

    st.caption(
        "Comet positions are approximate. "
        "For precise ephemeris data visit "
        "minorplanetcenter.net or heavens-above.com"
    )

# ═══════════════════════════════════════════════════════
# TAB 16 — Observatory Reviews
# ═══════════════════════════════════════════════════════
with tab16:
    st.subheader("⭐ Observatory Reviews & Ratings")
    st.caption(
        "Share your experience visiting observatories "
        "worldwide. Rate seeing conditions, darkness, "
        "and accessibility. Help other astronomers "
        "plan their visits."
    )

    # ── Summary metrics ───────────────────────────────────
    recent   = get_recent_reviews(limit=100)
    top_rated = get_top_rated_observatories(limit=20)

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Total Reviews",
              len(recent) if not recent.empty else 0)
    r2.metric("Observatories Reviewed",
              len(top_rated) if not top_rated.empty else 0)
    if not top_rated.empty:
        r3.metric("Highest Rated",
                  top_rated.iloc[0]["observatory"]
                  .replace(" Observatory", "")[:20])
        r4.metric("Top Rating",
                  f"{top_rated.iloc[0]['avg_rating']}/5")
    else:
        r3.metric("Highest Rated", "No reviews yet")
        r4.metric("Top Rating",    "—")

    st.markdown("---")

    # ── Tabs within tab ───────────────────────────────────
    rev_tab1, rev_tab2, rev_tab3 = st.tabs([
        "📝 Write a Review",
        "🔍 Browse Reviews",
        "🏆 Top Rated"
    ])

    # ── Write a review ────────────────────────────────────
    with rev_tab1:
        st.subheader("Share your experience")

        with st.form("review_form"):
            # Observatory selector
            rev_obs = st.selectbox(
                "Observatory visited",
                df["observatory"].tolist(),
                key="rev_obs"
            )

            # Reviewer name
            rev_name = st.text_input(
                "Your name or username",
                placeholder="e.g. AstroEnthusiast99"
            )

            # Overall rating
            st.markdown("**Overall rating**")
            rev_rating = st.slider(
                "Overall rating",
                min_value=1,
                max_value=5,
                value=4,
                key="rev_rating"
            )
            st.markdown(stars(rev_rating))

            # Sub-ratings
            st.markdown("**Detailed ratings**")
            sub1, sub2, sub3 = st.columns(3)
            with sub1:
                seeing_r = st.slider(
                    "Seeing conditions",
                    1, 5, 4,
                    key="seeing_r",
                    help="1 = very poor, 5 = exceptional"
                )
                st.caption(stars(seeing_r))
            with sub2:
                dark_r = st.slider(
                    "Sky darkness",
                    1, 5, 4,
                    key="dark_r",
                    help="1 = heavily light polluted, 5 = pristine dark sky"
                )
                st.caption(stars(dark_r))
            with sub3:
                access_r = st.slider(
                    "Accessibility",
                    1, 5, 3,
                    key="access_r",
                    help="1 = very difficult to reach, 5 = easy access"
                )
                st.caption(stars(access_r))

            # Visit details
            st.markdown("**Visit details**")
            d1, d2 = st.columns(2)
            with d1:
                visit_date = st.date_input(
                    "Date of visit",
                    key="visit_date"
                )
            with d2:
                telescope = st.text_input(
                    "Telescope used",
                    placeholder="e.g. 10-inch Dobsonian"
                )

            objects = st.text_input(
                "Objects observed",
                placeholder="e.g. M42, Jupiter, Andromeda Galaxy"
            )

            # Review text
            review_text = st.text_area(
                "Your review",
                placeholder=(
                    "Describe your experience — "
                    "seeing conditions, what you observed, "
                    "tips for other visitors..."
                ),
                height=150
            )

            submitted = st.form_submit_button(
                "Submit Review",
                type="primary"
            )

            if submitted:
                if not rev_name:
                    st.error(
                        "Please enter your name.")
                elif not review_text:
                    st.error(
                        "Please write a review.")
                else:
                    success, msg = add_review(
                        observatory      = rev_obs,
                        reviewer_name    = rev_name,
                        rating           = rev_rating,
                        review_text      = review_text,
                        visit_date       = str(
                            visit_date),
                        telescope_used   = telescope,
                        objects_observed = objects,
                        seeing_rating    = seeing_r,
                        darkness_rating  = dark_r,
                        access_rating    = access_r
                    )
                    if success:
                        st.success(
                            f"✅ Thank you {rev_name}! "
                            f"Your review of {rev_obs} "
                            f"has been submitted."
                        )
                        st.balloons()
                    else:
                        st.error(msg)

    # ── Browse reviews ────────────────────────────────────
    with rev_tab2:
        st.subheader("Browse observatory reviews")

        browse_obs = st.selectbox(
            "Select observatory",
            ["All observatories"] +
            df["observatory"].tolist(),
            key="browse_obs"
        )

        if browse_obs == "All observatories":
            reviews_df = get_recent_reviews(limit=50)
            stats      = None
        else:
            reviews_df = get_reviews(
                observatory=browse_obs, limit=50)
            stats      = get_observatory_stats(
                browse_obs)

        # Show stats for selected observatory
        if stats and stats["total_reviews"]:
            st.markdown("---")
            st.subheader(
                f"Stats for {browse_obs}")

            color = rating_color(stats["avg_rating"])
            st.markdown(
                f"<div style='background:{color}22;"
                f"border:2px solid {color};"
                f"border-radius:8px;"
                f"padding:16px;margin-bottom:16px'>"
                f"<div style='font-size:36px;"
                f"font-weight:bold;color:{color}'>"
                f"{'⭐' * int(round(float(stats['avg_rating'])))}"
                f"</div>"
                f"<div style='font-size:24px;"
                f"color:{color};font-weight:bold'>"
                f"{stats['avg_rating']} / 5</div>"
                f"<div style='color:#888;font-size:13px'>"
                f"Based on {stats['total_reviews']} "
                f"{'review' if stats['total_reviews'] == 1 else 'reviews'}"
                f"</div></div>",
                unsafe_allow_html=True
            )

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Reviews",
                      stats["total_reviews"])
            s2.metric("Avg Seeing",
                      f"{stats['avg_seeing']}/5"
                      if stats["avg_seeing"] else "N/A")
            s3.metric("Avg Darkness",
                      f"{stats['avg_darkness']}/5"
                      if stats["avg_darkness"] else "N/A")
            s4.metric("Avg Access",
                      f"{stats['avg_access']}/5"
                      if stats["avg_access"] else "N/A")

            # Rating distribution chart
            dist = get_rating_distribution(browse_obs)
            if not dist.empty:
                import matplotlib.pyplot as plt
                import io

                fig, ax = plt.subplots(figsize=(6, 2))
                all_ratings = {1: 0, 2: 0,
                               3: 0, 4: 0, 5: 0}
                for _, row in dist.iterrows():
                    all_ratings[row["rating"]] = \
                        row["count"]

                rating_labels = [
                    f"{'⭐' * r}" for r in range(5, 0, -1)]
                rating_vals   = [
                    all_ratings[r]
                    for r in range(5, 0, -1)]
                bar_colors    = [
                    "#1D9E75", "#378ADD",
                    "#EF9F27", "#E24B4A", "#888"
                ]

                ax.barh(
                    rating_labels,
                    rating_vals,
                    color=bar_colors,
                    height=0.6
                )
                for i, val in enumerate(rating_vals):
                    if val > 0:
                        ax.text(
                            val + 0.05, i,
                            str(val),
                            va="center",
                            color="white",
                            fontsize=9
                        )
                ax.set_xlabel(
                    "Number of reviews",
                    color="white", fontsize=8)
                ax.set_facecolor("#0E1117")
                fig.patch.set_facecolor("#0E1117")
                ax.tick_params(
                    colors="white", labelsize=9)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("#444441")
                ax.spines["bottom"].set_color(
                    "#444441")

                buf = io.BytesIO()
                plt.tight_layout()
                plt.savefig(
                    buf, format="png", dpi=120,
                    facecolor="#0E1117",
                    bbox_inches="tight"
                )
                buf.seek(0)
                img_data = buf.getvalue()
                buf.close()
                st.image(img_data, width="stretch")
                plt.close()

        st.markdown("---")

        # Display reviews
        if reviews_df is None or reviews_df.empty:
            st.info(
                "No reviews yet for this observatory. "
                "Be the first to leave a review!"
            )
        else:
            st.subheader(
                f"{len(reviews_df)} "
                f"{'review' if len(reviews_df) == 1 else 'reviews'}"
            )

            for _, rev in reviews_df.iterrows():
                rating    = rev.get("rating", 0)
                color     = rating_color(rating)
                name      = rev.get(
                    "reviewer_name", "Anonymous")
                date      = str(rev.get(
                    "created_at", ""))[:10]
                visit     = rev.get(
                    "visit_date", "")
                telescope = rev.get(
                    "telescope_used", "")
                objects   = rev.get(
                    "objects_observed", "")
                text      = rev.get(
                    "review_text", "")

                # Show observatory name if browsing all
                obs_header = ""
                if browse_obs == "All observatories":
                    obs_header = (
                        f"**{rev.get('observatory', '')}**"
                        f" · "
                    )

                with st.expander(
                    f"{'⭐' * int(rating)} "
                    f"{obs_header}"
                    f"**{name}** · "
                    f"{'Visited ' + str(visit) if visit else ''} "
                    f"· Reviewed {date}"
                ):
                    st.markdown(
                        f"<div style='background:{color}11;"
                        f"border-left:3px solid {color};"
                        f"padding:12px;border-radius:4px;"
                        f"margin-bottom:8px'>"
                        f"{text}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    if telescope or objects:
                        d1, d2 = st.columns(2)
                        if telescope:
                            d1.caption(
                                f"🔭 {telescope}")
                        if objects:
                            d2.caption(
                                f"🌌 {objects}")

                    sr = rev.get("seeing_rating")
                    dr = rev.get("darkness_rating")
                    ar = rev.get("access_rating")

                    if any([sr, dr, ar]):
                        sub1, sub2, sub3 = st.columns(3)
                        if sr:
                            sub1.metric(
                                "Seeing",
                                f"{'⭐' * int(sr)}")
                        if dr:
                            sub2.metric(
                                "Darkness",
                                f"{'⭐' * int(dr)}")
                        if ar:
                            sub3.metric(
                                "Access",
                                f"{'⭐' * int(ar)}")

    # ── Top rated ─────────────────────────────────────────
    with rev_tab3:
        st.subheader("🏆 Top rated observatories")
        st.caption(
            "Ranked by average visitor rating. "
            "Based on real reviews from astronomers "
            "who have visited these sites."
        )

        if top_rated.empty:
            st.info(
                "No reviews yet. Be the first to "
                "review an observatory!"
            )
        else:
            for i, (_, row) in enumerate(
                top_rated.iterrows()
            ):
                color  = rating_color(row["avg_rating"])
                medal  = (
                    "🥇" if i == 0
                    else "🥈" if i == 1
                    else "🥉" if i == 2
                    else f"#{i+1}"
                )

                with st.expander(
                    f"{medal} **{row['observatory']}** "
                    f"— {'⭐' * int(round(float(row['avg_rating'])))} "
                    f"({row['avg_rating']}/5) · "
                    f"{row['total_reviews']} "
                    f"{'review' if row['total_reviews'] == 1 else 'reviews'}"
                ):
                    t1, t2, t3, t4 = st.columns(4)
                    t1.metric("Overall",
                              f"{row['avg_rating']}/5")
                    t2.metric("Seeing",
                              f"{row['avg_seeing']}/5"
                              if row["avg_seeing"]
                              else "N/A")
                    t3.metric("Darkness",
                              f"{row['avg_darkness']}/5"
                              if row["avg_darkness"]
                              else "N/A")
                    t4.metric("Access",
                              f"{row['avg_access']}/5"
                              if row["avg_access"]
                              else "N/A")

                    if row.get("latest_visit"):
                        st.caption(
                            f"Latest visit: "
                            f"{row['latest_visit']}"
                        )

                    # Show latest review for this obs
                    latest = get_reviews(
                        observatory=row["observatory"],
                        limit=1
                    )
                    if not latest.empty:
                        rev = latest.iloc[0]
                        st.markdown(
                            f"*\"{rev['review_text']}\"*"
                        )
                        st.caption(
                            f"— {rev['reviewer_name']}"
                        )

        st.markdown("---")

        # Full table
        if not top_rated.empty:
            st.subheader("Full ratings table")
            top_display = top_rated[[
                "observatory", "total_reviews",
                "avg_rating", "avg_seeing",
                "avg_darkness", "avg_access"
            ]].rename(columns={
                "observatory":    "Observatory",
                "total_reviews":  "Reviews",
                "avg_rating":     "Overall",
                "avg_seeing":     "Seeing",
                "avg_darkness":   "Darkness",
                "avg_access":     "Access"
            })
            st.dataframe(
                top_display,
                hide_index=True,
                height=400
            )

            st.download_button(
                label="Download ratings as CSV",
                data=top_display.to_csv(index=False),
                file_name=f"observatory_ratings_"
                          f"{utcnow().strftime('%Y-%m-%d')}"
                          f".csv",
                mime="text/csv"
            )

# ═══════════════════════════════════════════════════════
# TAB 17 — Satellite Pass Predictor
# ═══════════════════════════════════════════════════════
with tab17:
    st.subheader("🛸 Satellite Pass Predictor")
    st.caption(
        "Predict when the ISS and other spacecraft pass "
        "over your selected observatory. Shows visible "
        "passes, brightness, direction and duration. "
        "All times in UTC."
    )

    # Observatory selector
    sat_obs = st.selectbox(
        "Select observatory",
        df["observatory"].tolist(),
        key="sat_obs"
    )
    sat_row = df[df["observatory"] == sat_obs].iloc[0]
    sat_lat = float(sat_row["latitude"])
    sat_lon = float(sat_row["longitude"])
    sat_alt = float(sat_row["altitude_m"] or 0)

    hours_ahead = st.slider(
        "Hours to look ahead",
        min_value=6,
        max_value=48,
        value=24,
        step=6,
        key="sat_hours"
    )

    with st.spinner(
        f"Calculating satellite passes for {sat_obs}..."
    ):
        sat_results = get_all_passes(
            sat_lat, sat_lon, sat_alt,
            hours_ahead=hours_ahead
        )

    # ── Summary metrics ───────────────────────────────────
    total_passes   = sum(
        len(s["passes"]) for s in sat_results.values())
    visible_passes = sum(
        1 for s in sat_results.values()
        for p in s["passes"] if p["is_visible"])
    bright_passes  = sum(
        1 for s in sat_results.values()
        for p in s["passes"]
        if p["is_visible"] and p["magnitude"] < 0)

    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("Total Passes",    total_passes)
    sm2.metric("Visible Tonight", visible_passes)
    sm3.metric("Bright Passes",   bright_passes)
    sm4.metric("Satellites",      len(sat_results))

    st.markdown("---")

    # ── ISS current position ──────────────────────────────
    st.subheader("🛸 ISS — Current Position")

    iss_data = sat_results.get("ISS", {})
    iss_pos  = iss_data.get("position")

    if iss_pos:
        ip1, ip2, ip3, ip4 = st.columns(4)
        ip1.metric("Altitude",
                   f"{iss_pos['altitude']}°",
                   "Above horizon" if iss_pos["visible"]
                   else "Below horizon")
        ip2.metric("Azimuth",
                   f"{iss_pos['azimuth']}° "
                   f"({iss_pos['direction']})")
        ip3.metric("Range",
                   f"{iss_pos['range_km']:,} km")
        ip4.metric("Currently",
                   "🌟 Overhead!" if iss_pos["visible"]
                   else "🌍 Below horizon")

        if iss_pos.get("sublat") is not None:
            st.caption(
                f"ISS ground track: "
                f"{iss_pos['sublat']}°N, "
                f"{iss_pos['sublong']}°E — "
                f"[Track on map →]"
                f"(https://www.n2yo.com/?s=25544)"
            )

    st.markdown("---")

    # ── Pass predictions ──────────────────────────────────
    for sat_key, sat_data in sat_results.items():
        passes  = sat_data["passes"]
        sat_name = sat_data["name"]
        icon    = sat_data.get("icon", "🛰️")
        color   = sat_data.get("color", "#4ECDC4")

        if not passes:
            continue

        visible = [p for p in passes if p["is_visible"]]
        st.subheader(
            f"{icon} {sat_name} — "
            f"{len(passes)} passes · "
            f"{len(visible)} visible"
        )

        for p in passes:
            if p["is_visible"]:
                status_emoji = "✅"
                status_text  = "VISIBLE"
                exp_color    = "#1D9E75"
            elif p["is_night"]:
                status_emoji = "🌙"
                status_text  = "Night — satellite in shadow"
                exp_color    = "#378ADD"
            else:
                status_emoji = "☀️"
                status_text  = "Daytime — too bright to see"
                exp_color    = "#888"

            with st.expander(
                f"{status_emoji} "
                f"{p['day_name']} "
                f"{p['rise_time']} → {p['set_time']} · "
                f"Max altitude: {p['max_alt']}° · "
                f"Mag: {p['magnitude']} "
                f"{p['mag_emoji']} · "
                f"{p['rise_dir']} → {p['set_dir']} · "
                f"{status_text}"
            ):
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Rise Time",   p["rise_time"])
                c2.metric("Max Alt",
                          f"{p['max_alt']}°")
                c3.metric("Set Time",    p["set_time"])
                c4.metric("Duration",    p["duration_str"])
                c5.metric("Brightness",
                          f"Mag {p['magnitude']}")

                d1, d2, d3 = st.columns(3)
                d1.metric("Rises in",    p["rise_dir"])
                d2.metric("Sets in",     p["set_dir"])
                d3.metric("Sun altitude",
                          f"{p['sun_alt']}°")

                st.info(
                    f"**{p['mag_emoji']} "
                    f"{p['mag_desc']}** — "
                    f"Look {p['rise_dir']} at "
                    f"{p['rise_time']} and track "
                    f"to {p['set_dir']}. "
                    f"Maximum altitude of "
                    f"{p['max_alt']}° reached at "
                    f"{p['max_time']}. "
                    f"Pass lasts {p['duration_str']}."
                )

                if p["is_visible"]:
                    st.success(
                        f"✅ This is a **visible pass** — "
                        f"the satellite will be bright enough "
                        f"to see with the naked eye from "
                        f"{sat_obs}. "
                        f"Set an alarm for {p['rise_time']}!"
                    )

        st.markdown("---")

    # ── Visibility calendar ───────────────────────────────
    st.subheader("📅 Visible passes summary")

    all_visible = []
    for sat_key, sat_data in sat_results.items():
        for p in sat_data["passes"]:
            if p["is_visible"]:
                all_visible.append({
                    "Satellite":  sat_data["name"],
                    "Date":       p["date_str"],
                    "Day":        p["day_name"],
                    "Rise":       p["rise_time"],
                    "Max Alt":    f"{p['max_alt']}°",
                    "Set":        p["set_time"],
                    "Duration":   p["duration_str"],
                    "Brightness": f"Mag {p['magnitude']}",
                    "Direction":  f"{p['rise_dir']} → {p['set_dir']}"
                })

    if all_visible:
        st.dataframe(
            pd.DataFrame(all_visible),
            hide_index=True,
            height=300
        )
        st.download_button(
            label="Download visible passes as CSV",
            data=pd.DataFrame(all_visible).to_csv(
                index=False),
            file_name=(
                f"satellite_passes_"
                f"{sat_obs.replace(' ', '_')}_"
                f"{utcnow().strftime('%Y-%m-%d')}.csv"),
            mime="text/csv"
        )
    else:
        st.info(
            "No visible passes in this window. "
            "Try extending the hours or check "
            "back later — the ISS completes an "
            "orbit every 90 minutes."
        )

    # ── Educational section ───────────────────────────────
    st.markdown("---")
    st.subheader("🎓 About satellite passes")
    st.markdown("""
**Why can I see the ISS?**
The ISS is large — roughly the size of a football
pitch — and covered in solar panels that reflect
sunlight. When it passes overhead during twilight
or night while sunlit, it appears as a fast-moving
bright dot crossing the sky in about 6 minutes.

**When is the best time to look?**
The ISS is only visible when it is in sunlight but
you are in darkness — typically 30 to 90 minutes
after sunset or before sunrise. Passes marked
✅ VISIBLE meet this condition.

**How bright does it get?**
At its brightest the ISS reaches magnitude -5 —
brighter than Venus and visible even in twilight.
Average passes are magnitude -1 to -3.

**How fast does it move?**
The ISS travels at 7.66 km/s — completing one orbit
every 92 minutes. A typical pass lasts 4 to 7 minutes
from horizon to horizon.

**Magnitude scale:**
- Mag -5: Extremely bright — unmissable
- Mag -3: Brighter than Jupiter  
- Mag -1: Similar to Sirius (brightest star)
- Mag 0 to 3: Easily visible naked eye
- Mag 4+: Binoculars needed
    """)

    st.caption(
        "Pass predictions use PyEphem with TLE data "
        "from Celestrak. Times are in UTC. "
        "TLE data updated daily for accuracy. "
        "For precise predictions visit "
        "heavens-above.com or n2yo.com"
    )

# ═══════════════════════════════════════════════════════
# TAB 17 — Observatory Detail
# ═══════════════════════════════════════════════════════
with tab17:
    st.subheader("🔬 Observatory Detail — Live View")
    st.caption(
        "Select any observatory for a complete live "
        "analysis calculated in real time. Weather data "
        "is updated hourly. Astronomical calculations "
        "are computed fresh when you select a site."
    )

    selected = st.selectbox(
        "Select an observatory",
        df["observatory"].tolist(),
        key="detail_obs"
    )

    row = df[df["observatory"] == selected].iloc[0]

    with st.spinner(
        f"Calculating live conditions for {selected}..."
    ):
        from live_calculator import calculate_live_conditions
        live = calculate_live_conditions(row)

    # ── Google Maps / Earth links ──────────────────────────
    gmap_url   = (
        f"https://www.google.com/maps/search/?api=1"
        f"&query={live['latitude']},{live['longitude']}"
    )
    gearth_url = (
        f"https://earth.google.com/web/@"
        f"{live['latitude']},{live['longitude']},"
        f"{live['altitude_m']}a,5000d,35y,0h,0t,0r"
    )
    street_url = (
        f"https://www.google.com/maps/@"
        f"{live['latitude']},{live['longitude']},14z"
    )

    link1, link2, link3 = st.columns(3)
    with link1:
        st.markdown(f"[🌍 Open in Google Earth]({gearth_url})")
    with link2:
        st.markdown(f"[🗺️ Open in Google Maps]({gmap_url})")
    with link3:
        st.markdown(f"[📍 Street View]({street_url})")

    # ── Header ────────────────────────────────────────────
    score = live["observation_score"]
    if score >= 80:   banner_color = "#1D9E75"
    elif score >= 60: banner_color = "#378ADD"
    elif score >= 40: banner_color = "#EF9F27"
    else:             banner_color = "#E24B4A"

    st.markdown(
        f"<div style='background:{banner_color}22;"
        f"border:2px solid {banner_color};"
        f"border-radius:8px;padding:16px;"
        f"margin-bottom:16px'>"
        f"<h3 style='color:{banner_color};margin:0'>"
        f"{selected}</h3>"
        f"<p style='color:#ccc;margin:4px 0 0'>"
        f"{live['country']} · "
        f"{live['altitude_m']}m altitude · "
        f"Score: {score}/100 · "
        f"Sky: {live['sky_state']}</p>"
        f"<p style='color:#888;font-size:12px;"
        f"margin:4px 0 0'>"
        f"Weather fetched: {live['fetch_datetime']} · "
        f"Calculated: {live['calculated_at']}</p>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Weather metrics ───────────────────────────────────
    st.subheader("Current weather")
    w1, w2, w3, w4, w5 = st.columns(5)
    w1.metric("Score",       f"{live['observation_score']}/100")
    w2.metric("Cloud Cover", f"{live['cloud_cover_pct']}%")
    w3.metric("Humidity",    f"{live['humidity_pct']}%")
    w4.metric("Wind Speed",  f"{live['wind_speed_ms']} m/s")
    w5.metric("Temperature", f"{live['temperature_c']}°C")

    st.markdown("---")

    # ── Sky state ─────────────────────────────────────────
    st.subheader("Current sky state")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Sky State",    live["sky_state"])
    s2.metric("Sun Altitude", f"{live['sun_altitude']}°")
    s3.metric("Moon Altitude",f"{live['moon_altitude']}°")
    s4.metric("Moon Phase",   f"{live['moon_phase_pct']}%")
    s5.metric("Is Dark Now",
              "Yes 🌑" if live["is_dark"] else "No ☀️")

    st.markdown("---")

    # ── Atmospheric analysis ──────────────────────────────
    st.subheader("Atmospheric conditions")
    a1, a2, a3 = st.columns(3)
    a1.metric("Seeing",
              f"{live['seeing_arcsec']}\"",
              live["seeing_quality"])
    a2.metric("PWV",
              f"{live['pwv_mm']} mm",
              live["pwv_quality"])
    a3.metric("Jet Stream",
              f"{live['jet_stream_ms']} m/s",
              live["jet_impact"])

    st.markdown("---")

    # ── Tonight's window ──────────────────────────────────
    st.subheader("Tonight's observing window")
    tw1, tw2, tw3, tw4, tw5 = st.columns(5)
    tw1.metric("Dark Start",  live["dark_start"])
    tw2.metric("Dark End",    live["dark_end"])
    tw3.metric("Dark Hours",  f"{live['dark_hours']}h")
    tw4.metric("Moon Rise",   live["moon_rise"])
    tw5.metric("Final Score", f"{live['final_score']}/100")

    st.markdown("---")

    # ── Peak observing time ───────────────────────────────
    st.subheader("Peak observing time tonight")
    p1, p2, p3 = st.columns(3)
    p1.metric("Peak Hour",   live["peak_hour"])
    p2.metric("Peak Score",  f"{live['peak_score']}/100")
    p3.metric("Good Hours",  f"{live['total_good_hours']}h")

    if live["hourly_data"]:
        hours  = [h["hour"] for h in live["hourly_data"]]
        scores = [h["combined_score"] for h in live["hourly_data"]]
        colors = []
        for s in scores:
            if s >= 80:   colors.append("#1D9E75")
            elif s >= 60: colors.append("#378ADD")
            elif s >= 40: colors.append("#EF9F27")
            elif s > 0:   colors.append("#E24B4A")
            else:         colors.append("#444441")

        fig, ax = plt.subplots(figsize=(12, 3))
        ax.bar(range(24), scores, color=colors, width=0.8)

        if scores:
            peak_idx = scores.index(max(scores))
            ax.bar(peak_idx, scores[peak_idx],
                   color="#1D9E75", width=0.8,
                   edgecolor="white", linewidth=2)

        ax.set_xticks(range(24))
        ax.set_xticklabels(
            [f"{h:02d}:00" for h in range(24)],
            rotation=45, fontsize=7)
        ax.set_ylim(0, 110)
        ax.set_ylabel("Score", fontsize=9)
        ax.set_title(
            f"Hourly observing score — {selected}",
            fontsize=10, fontweight="bold", color="white")
        ax.set_facecolor("#0E1117")
        fig.patch.set_facecolor("#0E1117")
        ax.tick_params(colors="white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#444441")
        ax.spines["bottom"].set_color("#444441")
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=120,
                    facecolor="#0E1117",
                    bbox_inches="tight")
        buf.seek(0)
        img_data = buf.getvalue()
        buf.close()
        plt.close(fig)
        st.image(img_data, width='stretch')

    st.markdown("---")

    # ── Website and live camera ───────────────────────────
    from sky_chart import get_observatory_url, get_live_camera

    obs_url = get_observatory_url(selected)
    st.markdown(
        f"🌐 **[Visit observatory website or search →]({obs_url})**"
    )

    cam = get_live_camera(selected)
    if cam:
        st.subheader("📷 Live Camera Feed")
        st.success(
            f"**{cam['name']}** — {cam['description']} · "
            f"Credit: {cam['credit']}"
        )
        st.markdown(f"[🔴 Open full live feed →]({cam['page_url']})")
        try:
            st.image(
                cam["image_url"],
                caption=f"Live feed — {cam['name']} — {cam['description']}",
                width='stretch'
            )
        except Exception:
            st.info(
                "Camera image unavailable right now. "
                f"[View directly →]({cam['page_url']})"
            )
    else:
        st.subheader("📷 Live Camera Feed")
        st.info(
            "No public live camera feed available "
            "for this observatory. Most smaller "
            "observatories do not publish live feeds."
        )

    st.markdown("---")
    st.info(
        f"**{selected}** is located at "
        f"{live['latitude']}°, {live['longitude']}° "
        f"in {live['country']} at {live['altitude_m']}m altitude. "
        f"All astronomical calculations are performed "
        f"live when you select this observatory."
    )