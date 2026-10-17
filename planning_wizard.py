"""
Guided observation-planning wizard for the GOWC dashboard.

Walks an observer through the full planning workflow, step by step:

    1. Target        — what to observe (magnitude, coordinates)
    2. Site          — which observatory
    3. Night         — which date
    4. Visibility    — is it up? airmass across the night
    5. Window        — when the sky is dark AND the target is high enough
    6. Conditions    — seeing, sky brightness, extinction for that night
    7. SNR/exposure  — exposure time to reach a target SNR (+ sigma_m)
    8. Plan summary  — the finished observing plan, exportable

Rendered by render_planning_wizard(); replaces the old Proposal Planner tab.
It reuses the same validated physics as the rest of GOWC (airmass, seeing,
SNR calculator), so the plan it produces is consistent with every other page.
"""
import math
import datetime as _dt

import streamlit as st

from object_visibility import OBJECTS
from airmass_calculator import (get_object_airmass_curve,
                                get_best_observation_window,
                                altitude_to_airmass)
from snr_calculator import (OBJECT_MAGNITUDES, PHOTOMETRIC_FILTERS,
                            calculate_snr, get_telescope_specs,
                            get_sky_brightness, is_extended_object)
from instruments import (list_facilities, list_instruments, list_filters,
                         get_instrument_config)
from observing_engine import W_AIRMASS, W_WEATHER, W_ALT, MIN_ALT_DEG

# Solar-system targets that are far too bright for CCD photometry and are
# observed instead with short video / lucky imaging.
_PLANETS = {"Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus",
            "Neptune", "Moon"}


def _step_header(n, total, title):
    st.markdown(f"**Step {n} of {total} · {title}**")


def render_planning_wizard(df, utcnow, load_atmospheric_cached):
    """Render the full guided planning wizard. `df` is the observatory table,
    `utcnow` a callable returning naive UTC now, `load_atmospheric_cached` a
    callable returning the atmospheric dataframe (seeing/pwv per site)."""

    TOTAL = 8

    # ══ STEP 1 — Target ═══════════════════════════════════════════
    _step_header(1, TOTAL, "Choose your target")
    _targetable = [k for k in OBJECT_MAGNITUDES if k in OBJECTS]
    c1, c2 = st.columns([2, 1])
    with c1:
        target = st.selectbox("Target object", _targetable, key="wiz_target")
    with c2:
        default_mag = float(OBJECT_MAGNITUDES.get(target, 10.0))
        mag = st.number_input("Magnitude", -5.0, 25.0, default_mag, 0.1,
                              # keyed per target: a fixed key keeps the old
                              # value when the target changes (Streamlit state)
                              key=f"wiz_mag_{target}",
                              help="Pre-filled from the catalogue; override for "
                                   "a custom target.")

    # ══ STEP 2 — Site (+ optional real instrument) ════════════════
    _step_header(2, TOTAL, "Choose the observatory")
    sc_a, sc_b = st.columns([2, 1])
    with sc_a:
        site = st.selectbox("Observatory", df["observatory"].tolist(),
                            key="wiz_site")
    site_row = df[df["observatory"] == site].iloc[0]
    lat = float(site_row["latitude"])
    lon = float(site_row["longitude"])
    alt_m = float(site_row.get("altitude_m", 0) or 0)

    # Optional real instrument. When chosen, its real filters (and constants)
    # drive Step 7 — so the filter list reflects what that telescope actually
    # carries, not a generic set. "Generic" keeps the standard filter set.
    with sc_b:
        _fac_opts = ["Generic (any filter)"] + list_facilities()
        wiz_facility = st.selectbox("Instrument (optional)", _fac_opts,
                                    key="wiz_facility",
                                    help="Pick a real telescope+instrument to "
                                         "use its actual filters and constants.")
    wiz_instrument = None
    if wiz_facility != "Generic (any filter)":
        _inst_opts = list_instruments(wiz_facility)
        wiz_instrument = st.selectbox("Instrument mode", _inst_opts,
                                      key="wiz_instrument")
        st.caption(f"Using **{wiz_facility} · {wiz_instrument}** — Step 7 will "
                   "show only this instrument's real filters.")

    # ══ STEP 3 — Night ════════════════════════════════════════════
    _step_header(3, TOTAL, "Choose the night")
    when_mode = st.radio("When", ["Tonight", "Pick a date"],
                        horizontal=True, key="wiz_when")
    if when_mode == "Pick a date":
        d = st.date_input("Date (UTC)", value=utcnow().date(), key="wiz_date")
        when = _dt.datetime.combine(d, _dt.time(23, 0))
    else:
        when = utcnow().replace(tzinfo=None)

    st.markdown("---")

    # ══ STEP 4 — Visibility ═══════════════════════════════════════
    _step_header(4, TOTAL, "Visibility — is it observable?")
    curve = get_object_airmass_curve(target, lat, lon, alt_m,
                                     date=when, hours=12)
    if not curve:
        st.warning(f"Could not compute a visibility curve for {target} at "
                   f"{site}. It may never rise there, or coordinates are "
                   "missing.")
        st.stop()

    dark_pts = [p for p in curve if p.get("is_dark") and p.get("airmass")]
    up_pts = [p for p in curve if p.get("airmass") and p["altitude"] > 0]
    if not up_pts:
        st.error(f"{target} stays below the horizon at {site} on this night — "
                 "not observable. Try another site or date.")
        st.stop()

    best_alt = max(p["altitude"] for p in up_pts)
    vc1, vc2, vc3 = st.columns(3)
    vc1.metric("Peak altitude", f"{best_alt:.0f}°")
    vc2.metric("Hours above horizon", f"{len(up_pts) * 0.5:.1f} h")
    vc3.metric("Dark hours it's up", f"{len(dark_pts) * 0.5:.1f} h")

    # Airmass-over-night chart
    import pandas as pd
    cdf = pd.DataFrame([{"time": p["time"], "airmass": p["airmass"],
                         "dark": p.get("is_dark", False)} for p in curve
                        if p.get("airmass")])
    if not cdf.empty:
        st.line_chart(cdf.set_index("time")["airmass"], height=180)
        st.caption("Airmass across the night (lower = better; 1.0 = zenith).")

    # ══ STEP 5 — Window ═══════════════════════════════════════════
    _step_header(5, TOTAL, "Best observing window")
    window = get_best_observation_window(curve)
    if window and window.get("best_time"):
        wc1, wc2, wc3 = st.columns(3)
        wc1.metric("Best time (UTC)", window["best_time"])
        wc2.metric("Best airmass", window["best_airmass"])
        wc3.metric("Good window", f"{window.get('good_hours', 0):.1f} h")
        if window.get("window_start"):
            st.caption(f"Target is well placed (airmass ≤ 2, dark sky) from "
                       f"**{window['window_start']}** to "
                       f"**{window['window_end']}** UTC.")
        best_airmass = window["best_airmass"] or 1.5
        best_alt_for_snr = math.degrees(math.asin(min(1.0, 1.0 / best_airmass)))
    elif dark_pts:
        # Up in darkness, but never below airmass 2: plan at the best DARK
        # altitude, not at the (possibly daylight) peak.
        best_alt_for_snr = max(p["altitude"] for p in dark_pts)
        best_airmass = altitude_to_airmass(max(1.0, best_alt_for_snr)) or 40.0
        st.warning(f"{target} is up in a dark sky only at low altitude (best "
                   f"{best_alt_for_snr:.0f}°, airmass {best_airmass:.2f}) on "
                   "this night. You can still plan, but conditions are "
                   "marginal.")
    else:
        best_alt_for_snr = best_alt
        best_airmass = altitude_to_airmass(max(1.0, best_alt)) or 40.0
        st.error(f"{target} is never above the horizon in a dark sky at {site} "
                 "on this night — it is only up in daylight or twilight. The "
                 "dark-sky conditions and exposure below do not apply; try "
                 "another date or site.")
    dark_ok = bool(dark_pts)

    st.markdown("---")

    # ══ STEP 6 — Conditions ═══════════════════════════════════════
    _step_header(6, TOTAL, "Conditions for the night")
    atm = load_atmospheric_cached()
    site_atm = atm[atm["observatory"] == site]
    seeing = 1.5
    pwv = None
    if not site_atm.empty:
        seeing = float(site_atm.iloc[0].get("seeing_arcsec") or 1.5)
        pwv = site_atm.iloc[0].get("pwv_mm")

    moon_choice = st.radio("Moon conditions",
                          ["Dark (new)", "Grey (quarter)", "Bright (full)"],
                          horizontal=True, key="wiz_moon")
    _mm = {"Dark (new)": (5, 0), "Grey (quarter)": (50, 30),
           "Bright (full)": (100, 60)}[moon_choice]
    sky_mag = get_sky_brightness(_mm[0], _mm[1])

    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Seeing", f"{seeing:.2f}\"")
    cc2.metric("Sky brightness", f"{sky_mag} mag/arcsec²")
    cc3.metric("PWV", f"{pwv:.1f} mm" if pwv else "—")

    # Target-weighted score: this target, this site, this night -- distinct
    # from the site's plain weather score (which doesn't know what you're
    # observing). Reuses rank_sites()'s exact formula/weights (observing_engine.py)
    # so the wizard and the observing-assistant chatbot never disagree on what
    # "good for this target" means. Shown alongside the raw airmass/seeing/SNR
    # numbers above and below, not instead of them -- the components are more
    # informative than one blended number, this is just a summary of them.
    weather_score = (float(site_atm.iloc[0]["weather_score"])
                      if not site_atm.empty else 50.0)
    _airmass_term = max(0.0, min(1.0, (2.5 - best_airmass) / 1.5))
    _alt_term = max(0.0, min(1.0, (best_alt_for_snr - MIN_ALT_DEG) / 60.0))
    target_score = round(100.0 * (W_AIRMASS * _airmass_term
                                  + W_WEATHER * (weather_score / 100.0)
                                  + W_ALT * _alt_term), 1)
    if not dark_ok:
        target_score = 0.0      # not observable in darkness on this night
    st.markdown("---")
    st.metric(f"Target-weighted score — {target} at {site}",
              f"{target_score:.0f}/100",
              help="Combines this target's airmass and altitude on this "
                   "specific night with the site's weather score, using the "
                   "same weighting as the observing-assistant chatbot "
                   f"(airmass {W_AIRMASS:.0%}, weather {W_WEATHER:.0%}, "
                   f"altitude {W_ALT:.0%}). Different from the site's plain "
                   "weather score shown elsewhere in GOWC, which does not "
                   "depend on what you're observing.")

    # ══ STEP 7 — SNR / exposure ═══════════════════════════════════
    st.markdown("---")
    _step_header(7, TOTAL, "Exposure & signal-to-noise")
    # Filter list comes from the chosen instrument when one is selected, so it
    # only offers filters that telescope actually carries; otherwise the
    # standard set. A resolved instrument config also supplies real constants.
    _inst_cfg_base = None
    if wiz_instrument:
        _filter_options = list_filters(wiz_facility, wiz_instrument)
    else:
        _filter_options = list(PHOTOMETRIC_FILTERS.keys())

    sc1, sc2 = st.columns(2)
    with sc1:
        _default_ix = _filter_options.index("V (visual)") \
            if "V (visual)" in _filter_options else 0
        filter_name = st.selectbox("Filter / band", _filter_options,
                                   index=_default_ix, key="wiz_filter")
    with sc2:
        target_snr = st.slider("Target SNR", 5, 200, 30, 5, key="wiz_snr")

    if mag <= 5 and (target in _PLANETS or not is_extended_object(target)):
        if target in _PLANETS:
            st.warning(f"{target} (V ≈ {mag}) is far too bright for CCD "
                       "photometry: it saturates a detector in milliseconds. "
                       "Planets are observed with short video bursts (lucky "
                       "imaging) on small telescopes, often in twilight.")
        else:
            st.warning(f"V ≈ {mag} is very bright: expect saturation in well "
                       "under a second on most telescopes. Use a neutral-"
                       "density filter, defocus, or a smaller telescope.")

    exposure_valid = dark_ok
    if not dark_ok:
        exposure_valid = st.checkbox(
            "Estimate anyway, assuming a dark sky (not realistic for this "
            "night)", value=False, key="wiz_est_anyway")

    if wiz_instrument:
        # Real instrument: resolved config carries specs + this filter's band,
        # wavelength, bandwidth and (where present) zero-point / efficiency.
        specs = get_instrument_config(wiz_facility, wiz_instrument, filter_name)
        filt = {"band": specs["band"], "wavelength_nm": specs["wavelength_nm"],
                "bandwidth_nm": specs["bandwidth_nm"]}
    else:
        filt = PHOTOMETRIC_FILTERS[filter_name]
        specs = get_telescope_specs(site, alt_m)

    # Solve exposure to reach the target SNR by scanning (SNR grows ~sqrt(t)
    # in the sky/read regime; a direct scan is robust across regimes).
    def _snr_at(t):
        r = calculate_snr(
            object_magnitude=mag, exposure_time_s=float(t),
            telescope_specs=specs, sky_brightness_mag=float(sky_mag),
            seeing_arcsec=seeing, object_name=target,
            object_altitude_deg=best_alt_for_snr, pwv_mm=pwv,
            site_altitude_m=alt_m, filter_band=filt["band"],
            wavelength_nm=filt["wavelength_nm"], bandwidth_nm=filt["bandwidth_nm"])
        return r

    # Bracket the exposure, then refine.
    # Search from 1 ms: bright targets reach the SNR in well under a second,
    # and a 1 s floor would report "1 s" with the (much higher) SNR at 1 s.
    t_lo, t_hi = 0.001, 36000.0
    r_hi = _snr_at(t_hi)
    if r_hi["snr"] < target_snr:
        req_t = None
        chosen = r_hi
    elif _snr_at(t_lo)["snr"] >= target_snr:
        req_t = t_lo
        chosen = _snr_at(t_lo)
    else:
        for _ in range(40):
            t_mid = math.sqrt(t_lo * t_hi)
            if _snr_at(t_mid)["snr"] < target_snr:
                t_lo = t_mid
            else:
                t_hi = t_mid
        req_t = t_hi
        chosen = _snr_at(req_t)

    if not exposure_valid:
        req_t = None            # no exposure is offered for a daylight target

    def _fmt_t(t):
        if not exposure_valid:
            return "not estimated (not up in darkness)"
        if t is None:
            return "Not reachable (>10 h)"
        if t <= 0.001:
            return "< 1 ms"
        if t < 1:
            return f"{t * 1000:.0f} ms"
        if t < 10:
            return f"{t:.1f} s"
        if t < 60:
            return f"{t:.0f} s"
        if t < 3600:
            return f"{t/60:.1f} min"
        return f"{t/3600:.2f} h"

    _sig = chosen.get("sigma_mag") if exposure_valid else None
    pred_snr = chosen["snr"] if exposure_valid else "not estimated"
    if not exposure_valid:
        st.info("Exposure not estimated: the target is not up in a dark sky on "
                "this night, so a dark-sky signal-to-noise would be "
                "misleading.")
    else:
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric(f"Exposure for SNR {target_snr}", _fmt_t(req_t))
        ec2.metric("Achieved SNR", chosen["snr"])
        ec3.metric("Mag uncertainty σ_m",
                   f"±{_sig}" if _sig else "—",
                   help="σ_m = 1.0857 / SNR — the photometric error on the "
                        "magnitude at this SNR.")
    if exposure_valid and chosen.get("is_saturated"):
        st.error("⚠️ Detector saturates at this exposure — shorten it or "
                 "defocus.")
    if exposure_valid and req_t is not None and req_t < 1:
        _r1 = _snr_at(1.0)
        st.warning(
            f"This target is bright: SNR {target_snr} needs only {_fmt_t(req_t)}, "
            "shorter than most CCD shutters allow (~1 s). A 1 s exposure gives "
            f"SNR {_r1['snr']}"
            + (" and **saturates the detector**" if _r1.get("is_saturated") else "")
            + ". Use a neutral-density filter, defocus, or a smaller telescope.")

    # ══ STEP 8 — Plan summary ═════════════════════════════════════
    st.markdown("---")
    _step_header(8, TOTAL, "Your observing plan")
    best_time = window.get("best_time") if window else None
    if best_time:
        window_line = f"around {best_time} UTC, airmass {round(best_airmass, 2)}"
    elif dark_ok:
        window_line = (f"none below airmass 2 in darkness; best dark airmass "
                       f"{round(best_airmass, 2)}")
    else:
        window_line = "none — target is not up in a dark sky on this night"
    plan = f"""OBSERVING PLAN
================
Target        : {target}   (V ≈ {mag})
Observatory   : {site}
Night         : {when.strftime('%Y-%m-%d')}
Moon          : {moon_choice}

Visibility    : peak altitude {best_alt:.0f}°, up {len(up_pts)*0.5:.1f} h
Best window   : {window_line}
Conditions    : seeing {seeing:.2f}", sky {sky_mag} mag/arcsec²{f', PWV {pwv:.1f} mm' if pwv else ''}

Filter        : {filter_name}
Exposure      : {_fmt_t(req_t)}  for SNR {target_snr}
Achieved SNR  : {pred_snr}  (σ_m = ±{_sig if _sig else '—'} mag)

Generated by GOWC — forecasts are planning estimates, not official
observatory conditions.
"""
    st.code(plan, language="text")
    st.download_button("⬇️ Download plan (.txt)", plan,
                       file_name=f"observing_plan_{target.split(' ')[0]}_"
                                 f"{when.strftime('%Y%m%d')}.txt",
                       mime="text/plain", key="wiz_download")
    st.caption("This plan uses the same validated airmass, seeing and SNR "
               "physics as the rest of GOWC.")

    # ══ STEP 8b — Formal proposal draft (PHY430 11-section) ═══════
    with st.expander("📄 Also generate a formal proposal draft "
                     "(PHY430 11-section format)"):
        st.caption("Pours this plan into the 11-section observing-proposal "
                   "structure. Sections 3–7 and 9 are filled from the wizard; "
                   "1, 2, 8, 10, 11 are your own input — the science case "
                   "especially must be your own work.")
        pc1, pc2 = st.columns(2)
        with pc1:
            pp_title = st.text_input("§1 Title (≤12 words)", key="wiz_pp_title",
                placeholder="e.g. Photometric monitoring of M31 novae")
            pp_backup = st.text_area("§10 Backup programme (≤50 words)",
                key="wiz_pp_backup", height=80)
        with pc2:
            pp_summary = st.text_area("§2 Summary (≤150 words)",
                key="wiz_pp_summary", height=80,
                placeholder="What you will observe and why.")
            pp_experience = st.text_area("§11 Previous experience (≤50 words)",
                key="wiz_pp_experience", height=80)

        # Target coordinates (J2000) for §6.
        info = OBJECTS.get(target, {})
        ra = info.get("ra") or (f"{info.get('ra_deg'):.4f}°"
                                if info.get("ra_deg") is not None else "—")
        dec = info.get("dec") or (f"{info.get('dec_deg'):.4f}°"
                                  if info.get("dec_deg") is not None else "—")
        # Observing time: exposure + ~40% overhead (acquisition, readout, etc.).
        obs_hours = ((req_t or 0) * 1.4 / 3600.0) if req_t else 0.0

        proposal = "\n".join([
            "OBSERVING PROPOSAL (draft)",
            "=" * 50, "",
            f"§1 TITLE: {pp_title or '[to complete]'}",
            "",
            "§2 SUMMARY:",
            f"  {pp_summary or '[to complete — max 150 words]'}",
            "",
            f"§3 OBSERVING TIME REQUIRED : {obs_hours:.2f} hours "
            "(single target, incl. ~40% overhead)",
            f"§4 MOON PHASE REQUIRED     : {moon_choice}",
            f"§5 PREFERRED DATE/TIME     : {when.strftime('%Y-%m-%d')} "
            + (f"around {best_time} UTC (dark, target well placed)"
               if best_time else f"— {window_line}"),
            "",
            f"Observatory                : {site} ({int(alt_m)} m)",
            f"Filter / band              : {filter_name}",
            f"Target SNR                 : {target_snr}",
            "",
            "§6 TARGET LIST (J2000):",
            f"  {target}  RA {ra}  Dec {dec}  V={mag}  "
            f"exp={_fmt_t(req_t)}  (best airmass {round(best_airmass, 2)})",
            "",
            "§7 FINDING CHARTS: produce externally (Aladin/DSS), ~5' N-up "
            "E-left.",
            "",
            "§8 SCIENTIFIC JUSTIFICATION: [~2000 words — your own work]",
            "",
            "§9 TECHNICAL JUSTIFICATION:",
            "  Exposure solved via the CCD signal-to-noise equation (shot + "
            f"sky + dark + read + scintillation noise) in the {filt['band']} "
            f"band, including airmass extinction at {int(alt_m)} m and "
            f"moon-dependent sky brightness ({sky_mag} mag/arcsec²). "
            f"Predicted SNR {pred_snr} (σ_m = ±{_sig if _sig else '—'} "
            "mag). SNR method validated against the ING SIGNAL ETC.",
            "",
            f"§10 BACKUP PROGRAMME: {pp_backup or '[to complete — max 50 words]'}",
            "",
            f"§11 PREVIOUS EXPERIENCE: {pp_experience or '[to complete — max 50 words]'}",
            "",
            "Generated by GOWC — gowcastroclimate.com",
        ])
        st.code(proposal, language="text")
        st.download_button("⬇️ Download proposal draft (.txt)", proposal,
                           file_name=f"observing_proposal_{target.split(' ')[0]}_"
                                     f"{when.strftime('%Y%m%d')}.txt",
                           mime="text/plain", key="wiz_pp_download")
