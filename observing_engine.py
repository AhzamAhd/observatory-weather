"""
Observing-assistant engine — Part A.

A transparent, rules-based ranking function. Given a target (RA/Dec) and a
date, it scores a fixed set of well-placed GOWC observatories on whether the
target is observable and how good the conditions are, and returns the ranked
sites plus the best observing-time window.

There is NO machine learning and NO LLM here. Every number this module
returns comes from deterministic astronomy (ephem) and GOWC's own weather
score. The chatbot layer (Part B) may only *relay* these numbers — it must
never compute or invent them.

Astro math uses ephem, which is verified against astropy to <0.001° on
altitude and identical astronomical-night classification (see the project's
scratch comparison). ephem is already GOWC's engine everywhere else, so the
engine's figures line up with the rest of the app and add no dependency.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import ephem


# ── Tunable thresholds (all explicit, so the ranking stays transparent) ──
MIN_ALT_DEG = 30.0        # target must clear this altitude to count as "up"
ASTRO_NIGHT_SUN_DEG = -18.0   # sun below this = astronomical darkness
STEP_MINUTES = 20         # sampling cadence when scanning the night

# Weighting of the final site score (documented so answers can explain it).
W_AIRMASS = 0.45          # lower airmass is better
W_WEATHER = 0.45          # GOWC current-conditions score
W_ALT = 0.10              # altitude margin above the minimum


# ── Curated observatory set: 8 well-placed sites, global longitude spread ──
# Coordinates are J2000 decimal degrees; elevations in metres (accurate site
# values — GOWC's DB altitude column is unreliable/zero for these). Chosen for
# real observing quality and even longitude coverage so at least one site is in
# darkness for almost any RA. Sites are matched to GOWC's live weather DB by
# NEAREST COORDINATE at query time (see rank_sites) — not by name, because
# GOWC uses MPC-style names that don't match clean site names. Every site here
# has a GOWC weather station within ~0.2° (verified).
OBSERVATORIES = [
    {"name": "Las Campanas", "lat": -28.8400, "lon": -70.7000, "elev_m": 2380, "country": "Chile"},
    {"name": "Cerro Tololo (CTIO)", "lat": -30.1690, "lon": -70.8060, "elev_m": 2207, "country": "Chile"},
    {"name": "Mauna Kea", "lat": 19.8207, "lon": -155.4681, "elev_m": 4205, "country": "USA"},
    {"name": "Roque de los Muchachos (La Palma)", "lat": 28.7606, "lon": -17.8814, "elev_m": 2396, "country": "Spain"},
    {"name": "SAAO Sutherland", "lat": -32.3794, "lon": 20.8107, "elev_m": 1798, "country": "South Africa"},
    {"name": "Siding Spring", "lat": -31.2733, "lon": 149.0644, "elev_m": 1165, "country": "Australia"},
    {"name": "Haleakala (Hawaii)", "lat": 20.7080, "lon": -156.2570, "elev_m": 3055, "country": "USA"},
    {"name": "Xingming (Mt. Nanshan)", "lat": 43.2800, "lon": 87.1800, "elev_m": 2080, "country": "China"},
]

# Max coordinate distance (degrees) to accept a GOWC weather station as
# representing an engine site. ~0.5° ≈ 55 km — close enough to share weather.
WEATHER_MATCH_TOL_DEG = 0.5


def _observer(site, when):
    obs = ephem.Observer()
    obs.lat = str(site["lat"])
    obs.long = str(site["lon"])
    obs.elevation = float(site["elev_m"])
    obs.pressure = 0            # ignore refraction — matches GOWC convention
    obs.date = when.strftime("%Y/%m/%d %H:%M:%S")
    return obs


def _airmass(alt_deg):
    """Kasten-Young (1989) airmass. Returns None below the horizon."""
    if alt_deg <= 0:
        return None
    za = 90.0 - alt_deg
    return 1.0 / (math.cos(math.radians(za)) + 0.50572 * (96.07995 - za) ** -1.6364)


def observe_at(ra_deg, dec_deg, site, when_utc):
    """Instantaneous geometry of a fixed target from one site.

    Returns altitude, airmass, sun altitude, and the two booleans the ranking
    depends on: target above MIN_ALT_DEG, and site in astronomical night.
    """
    obs = _observer(site, when_utc)
    body = ephem.FixedBody()
    # ephem._ra/_dec take radians; ephem.degrees() parses decimal degrees to
    # radians, so passing decimal-degree RA through it is correct (verified
    # against astropy — do not "fix" this to ephem.hours()).
    body._ra = ephem.degrees(str(ra_deg))
    body._dec = ephem.degrees(str(dec_deg))
    body.compute(obs)
    alt = math.degrees(float(body.alt))

    sun = ephem.Sun()
    sun.compute(obs)
    sun_alt = math.degrees(float(sun.alt))

    return {
        "alt_deg": alt,
        "airmass": _airmass(alt),
        "sun_alt_deg": sun_alt,
        "is_up": alt >= MIN_ALT_DEG,
        "is_astro_night": sun_alt <= ASTRO_NIGHT_SUN_DEG,
        "observable": alt >= MIN_ALT_DEG and sun_alt <= ASTRO_NIGHT_SUN_DEG,
    }


def _night_window(ra_deg, dec_deg, site, date_utc):
    """Scan the 24h from local-ish night start and return the best observable
    window for this target at this site: the contiguous stretch where the
    target is up AND it's astronomical night, with the minimum airmass in it.

    Returns dict or None if never observable that date.
    """
    # Scan a full 24h at STEP_MINUTES cadence starting at 12:00 UTC of the
    # date, which covers a whole night for every longitude.
    start = datetime(date_utc.year, date_utc.month, date_utc.day, 12, 0, 0)
    samples = []
    for i in range(int(24 * 60 / STEP_MINUTES) + 1):
        t = start + timedelta(minutes=i * STEP_MINUTES)
        r = observe_at(ra_deg, dec_deg, site, t)
        samples.append((t, r))

    # Find the longest contiguous observable run; track min airmass + its time.
    best = None
    run_start = None
    run_min_am = None
    run_min_am_t = None

    def close_run(run_start, run_end, min_am, min_am_t):
        nonlocal best
        dur_h = (run_end - run_start).total_seconds() / 3600.0
        cand = {
            "start_utc": run_start,
            "end_utc": run_end,
            "duration_hours": round(dur_h, 2),
            "min_airmass": round(min_am, 3) if min_am else None,
            "best_time_utc": min_am_t,
        }
        if best is None or dur_h > best["duration_hours"]:
            best = cand

    prev_t = None
    for t, r in samples:
        if r["observable"]:
            if run_start is None:
                run_start = t
                run_min_am = r["airmass"]
                run_min_am_t = t
            elif r["airmass"] is not None and (run_min_am is None or r["airmass"] < run_min_am):
                run_min_am = r["airmass"]
                run_min_am_t = t
            prev_t = t
        else:
            if run_start is not None:
                close_run(run_start, prev_t, run_min_am, run_min_am_t)
                run_start = None
    if run_start is not None:
        close_run(run_start, prev_t, run_min_am, run_min_am_t)

    return best


def _nearest_weather(site, weather_rows):
    """Return (score, True) for the nearest GOWC weather station within
    WEATHER_MATCH_TOL_DEG of the site, else (50.0, False) neutral default.

    weather_rows: iterable of {"latitude", "longitude", "observation_score"}.
    """
    best_score = None
    best_d = WEATHER_MATCH_TOL_DEG
    for r in weather_rows:
        try:
            d = math.hypot(site["lat"] - float(r["latitude"]),
                           site["lon"] - float(r["longitude"]))
        except (TypeError, ValueError):
            continue
        if d <= best_d:
            best_d = d
            best_score = r.get("observation_score")
    if best_score is not None:
        return float(best_score), True
    return 50.0, False


def rank_sites(ra_deg, dec_deg, date_utc=None, weather_rows=None):
    """Rank the observatory set for a target on a given UTC date.

    weather_rows: optional iterable of GOWC live rows, each with
    "latitude", "longitude", and "observation_score" (0-100). Each engine site
    is matched to the nearest station within WEATHER_MATCH_TOL_DEG; sites with
    no nearby station fall back to a neutral 50 and are flagged weather_known
    False.

    Returns a dict:
      {
        "target": {"ra_deg", "dec_deg"},
        "date_utc": "YYYY-MM-DD",
        "ranked": [ {site, observable, best window, airmass, weather, score}, ... ],
        "best_site": <the top observable site or None>,
      }
    Deterministic and LLM-free. Higher score = better.
    """
    if date_utc is None:
        date_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    weather_rows = list(weather_rows or [])

    ranked = []
    for site in OBSERVATORIES:
        window = _night_window(ra_deg, dec_deg, site, date_utc)
        observable = window is not None

        weather, weather_known = _nearest_weather(site, weather_rows)

        if observable:
            min_am = window["min_airmass"] or 3.0
            # airmass 1.0 -> 1.0, airmass 2.5+ -> ~0. Linear, clamped.
            airmass_term = max(0.0, min(1.0, (2.5 - min_am) / 1.5))
            # altitude margin: how far above MIN_ALT the target's best moment is.
            best_r = observe_at(ra_deg, dec_deg, site, window["best_time_utc"])
            alt_term = max(0.0, min(1.0, (best_r["alt_deg"] - MIN_ALT_DEG) / 60.0))
            score = round(
                100.0 * (W_AIRMASS * airmass_term
                         + W_WEATHER * (weather / 100.0)
                         + W_ALT * alt_term), 1)
        else:
            min_am = None
            score = 0.0

        ranked.append({
            "site": site["name"],
            "country": site["country"],
            "observable": observable,
            "min_airmass": min_am,
            "best_time_utc": (window["best_time_utc"].strftime("%Y-%m-%d %H:%M UTC")
                              if observable else None),
            "window_start_utc": (window["start_utc"].strftime("%H:%M")
                                 if observable else None),
            "window_end_utc": (window["end_utc"].strftime("%H:%M")
                               if observable else None),
            "window_hours": window["duration_hours"] if observable else 0.0,
            "weather_score": round(weather, 1),
            "weather_known": weather_known,
            "score": score,
        })

    ranked.sort(key=lambda r: (r["observable"], r["score"]), reverse=True)
    best = next((r for r in ranked if r["observable"]), None)

    return {
        "target": {"ra_deg": ra_deg, "dec_deg": dec_deg},
        "date_utc": date_utc.strftime("%Y-%m-%d"),
        "ranked": ranked,
        "best_site": best,
    }


# A small built-in catalog so the assistant can resolve common target names to
# coordinates WITHOUT the LLM inventing them. The LLM may only pick a name from
# here or pass through explicit user-supplied RA/Dec.
KNOWN_TARGETS = {
    "vela x-1":   (135.5286, -40.5547),
    "sco x-1":    (244.9793, -15.6403),
    "cyg x-1":    (299.5903, 35.2016),
    "cen x-3":    (170.3133, -60.6238),
    "her x-1":    (254.4575, 35.3424),
    "gx 339-4":   (255.7058, -48.7896),
    "crab nebula": (83.6331, 22.0145),
    "m31":        (10.6847, 41.2687),
    "sn 1987a":   (83.8667, -69.2694),
}


def resolve_target(name):
    """Return (ra_deg, dec_deg) for a known target name, or None."""
    return KNOWN_TARGETS.get(name.strip().lower())


if __name__ == "__main__":
    # Standalone smoke run — no LLM, no network.
    ra, dec = resolve_target("Vela X-1")
    result = rank_sites(ra, dec, datetime(2026, 8, 13))
    print(f"Target Vela X-1 ({ra}, {dec})  date {result['date_utc']}\n")
    for r in result["ranked"]:
        obs = "UP " if r["observable"] else "-- "
        am = f"am {r['min_airmass']:.2f}" if r["min_airmass"] else "am  -  "
        bt = r["best_time_utc"] or "not observable"
        print(f"  {obs} {r['site']:34s} score {r['score']:5.1f}  {am}  best {bt}")
    print(f"\nBEST: {result['best_site']['site'] if result['best_site'] else 'none'}")
