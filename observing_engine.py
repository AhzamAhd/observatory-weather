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
    return _result_from_body(body, obs)


def _result_from_body(body, obs):
    """Shared result builder given a computed ephem body and observer."""
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


# ── Solar-system bodies (Moon, planets): position changes over the night,
# so they're recomputed at each time step rather than from a fixed RA/Dec. ──
SOLAR_SYSTEM = {
    "moon": ephem.Moon, "mercury": ephem.Mercury, "venus": ephem.Venus,
    "mars": ephem.Mars, "jupiter": ephem.Jupiter, "saturn": ephem.Saturn,
    "uranus": ephem.Uranus, "neptune": ephem.Neptune, "sun": ephem.Sun,
}


def resolve_solar_system(name):
    """Return an ephem body class for a Moon/planet name, or None.

    Matches on whole-word tokens so "the Moon", "planet Jupiter", "Moon
    tonight" all resolve, without misfiring on substrings.
    """
    if not name:
        return None
    tokens = set(_norm(name).split())
    for key, cls in SOLAR_SYSTEM.items():
        if key in tokens:
            return cls
    return None


def observe_body_at(body_cls, site, when_utc):
    """Observability of a moving solar-system body from one site at a time."""
    obs = _observer(site, when_utc)
    body = body_cls()
    body.compute(obs)
    return _result_from_body(body, obs)


def _night_window(ra_deg, dec_deg, site, date_utc, body_cls=None):
    """Scan the 24h from local-ish night start and return the best observable
    window for this target at this site: the contiguous stretch where the
    target is up AND it's astronomical night, with the minimum airmass in it.

    If body_cls is given (a Moon/planet ephem class), the moving body's
    position is recomputed at each step; otherwise the fixed ra/dec is used.

    Returns dict or None if never observable that date.
    """
    # Scan a full 24h at STEP_MINUTES cadence starting at 12:00 UTC of the
    # date, which covers a whole night for every longitude.
    start = datetime(date_utc.year, date_utc.month, date_utc.day, 12, 0, 0)
    samples = []
    for i in range(int(24 * 60 / STEP_MINUTES) + 1):
        t = start + timedelta(minutes=i * STEP_MINUTES)
        if body_cls is not None:
            r = observe_body_at(body_cls, site, t)
        else:
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


def rank_sites(ra_deg, dec_deg, date_utc=None, weather_rows=None, body_cls=None):
    """Rank the observatory set for a target on a given UTC date.

    weather_rows: optional iterable of GOWC live rows, each with
    "latitude", "longitude", and "observation_score" (0-100). Each engine site
    is matched to the nearest station within WEATHER_MATCH_TOL_DEG; sites with
    no nearby station fall back to a neutral 50 and are flagged weather_known
    False.

    body_cls: optional ephem body class for a moving solar-system object
    (Moon/planet). When given, ra_deg/dec_deg are ignored and the body's
    position is recomputed over the night.

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
        window = _night_window(ra_deg, dec_deg, site, date_utc, body_cls=body_cls)
        observable = window is not None

        weather, weather_known = _nearest_weather(site, weather_rows)

        if observable:
            min_am = window["min_airmass"] or 3.0
            # airmass 1.0 -> 1.0, airmass 2.5+ -> ~0. Linear, clamped.
            airmass_term = max(0.0, min(1.0, (2.5 - min_am) / 1.5))
            # altitude margin: how far above MIN_ALT the target's best moment is.
            if body_cls is not None:
                best_r = observe_body_at(body_cls, site, window["best_time_utc"])
            else:
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
# Built-in fallbacks — a few famous objects that aren't in the transient
# catalog. The full resolvable set is these PLUS every transient-catalog target
# (X-ray binaries, live MAXI alerts, etc.), merged in build_target_index().
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

# Class keywords → the transient-catalog classes they map to. Lets the
# assistant answer "where can I observe neutron stars / X-ray binaries?" by
# listing the matching catalog targets instead of refusing.
_CLASS_KEYWORDS = {
    "neutron star": ["Neutron-star X-ray binaries (LMXB/HMXB)"],
    "ns-xrb": ["Neutron-star X-ray binaries (LMXB/HMXB)"],
    "lmxb": ["Neutron-star X-ray binaries (LMXB/HMXB)"],
    "hmxb": ["Neutron-star X-ray binaries (LMXB/HMXB)"],
    "black hole": ["Black-hole X-ray binaries"],
    "black-hole": ["Black-hole X-ray binaries"],
    "bh-xrb": ["Black-hole X-ray binaries"],
    "x-ray binary": ["Neutron-star X-ray binaries (LMXB/HMXB)",
                     "Black-hole X-ray binaries"],
    "x-ray binaries": ["Neutron-star X-ray binaries (LMXB/HMXB)",
                       "Black-hole X-ray binaries"],
    "xrb": ["Neutron-star X-ray binaries (LMXB/HMXB)",
            "Black-hole X-ray binaries"],
}


def _norm(s):
    """Normalise a target name for matching: lowercase, collapse spaces, drop
    punctuation that varies between how people write catalog names."""
    import re
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


_TARGET_INDEX = None   # {normalised_name: {"display", "ra_deg", "dec_deg", "kind"}}


def build_target_index():
    """Merge the built-in targets with every transient-catalog target that has
    coordinates. Cached after first build. Import failure of transients is
    tolerated (the assistant still works with the built-ins)."""
    global _TARGET_INDEX
    if _TARGET_INDEX is not None:
        return _TARGET_INDEX

    idx = {}
    for name, (ra, dec) in KNOWN_TARGETS.items():
        idx[_norm(name)] = {"display": name.title(), "ra_deg": ra,
                            "dec_deg": dec, "kind": None}

    try:
        import transients as T
        for cls in ("Neutron-star X-ray binaries (LMXB/HMXB)",
                    "Black-hole X-ray binaries"):
            for t in T.get_targets(cls):
                if t.get("ra_deg") is None or t.get("dec_deg") is None:
                    continue
                key = _norm(t["name"])
                if key and key not in idx:
                    idx[key] = {"display": t["name"], "ra_deg": t["ra_deg"],
                                "dec_deg": t["dec_deg"], "kind": t.get("kind")}
                # also index the alt_name if present
                alt = t.get("alt_name")
                if alt and _norm(alt) not in idx:
                    idx[_norm(alt)] = {"display": t["name"], "ra_deg": t["ra_deg"],
                                       "dec_deg": t["dec_deg"], "kind": t.get("kind")}
    except Exception:
        pass

    _TARGET_INDEX = idx
    return idx


def resolve_target(name):
    """Return (ra_deg, dec_deg) for a target name, or None.

    Matching order: exact normalised, then close fuzzy match (difflib). Only
    returns a single confident hit — for ambiguous/class queries use
    find_targets() instead.
    """
    if not name:
        return None
    idx = build_target_index()
    key = _norm(name)
    if key in idx:
        e = idx[key]
        return (e["ra_deg"], e["dec_deg"])
    # fuzzy: accept a single high-confidence match
    import difflib
    hits = difflib.get_close_matches(key, list(idx.keys()), n=1, cutoff=0.82)
    if hits:
        e = idx[hits[0]]
        return (e["ra_deg"], e["dec_deg"])
    return None


def find_targets(query, limit=8):
    """Return a list of candidate targets for an ambiguous or class query.

    Each item: {"display", "ra_deg", "dec_deg", "kind"}. Handles:
      - a class keyword ("neutron stars", "x-ray binaries") -> list that class
      - a partial/typo name -> fuzzy + substring matches
    Empty list if nothing plausible. LLM-free.
    """
    idx = build_target_index()
    qn = _norm(query)

    # 1) class keyword? (normalise the keyword the same way as the query)
    for kw, classes in _CLASS_KEYWORDS.items():
        if _norm(kw) in qn:
            out = []
            try:
                import transients as T
                for cls in classes:
                    for t in T.get_targets(cls):
                        if t.get("ra_deg") is not None:
                            out.append({"display": t["name"], "ra_deg": t["ra_deg"],
                                        "dec_deg": t["dec_deg"], "kind": t.get("kind")})
            except Exception:
                pass
            # dedup by display name, keep order
            seen = set(); uniq = []
            for o in out:
                if o["display"] not in seen:
                    seen.add(o["display"]); uniq.append(o)
            return uniq[:limit]

    # 2) substring + fuzzy name matches. Dedup by DISPLAY name (alt_name keys
    #    point at the same object) so the same target isn't listed twice.
    import difflib
    subs = [k for k in idx if qn and qn in k]
    fuzzy = difflib.get_close_matches(qn, list(idx.keys()), n=limit * 2, cutoff=0.6)
    out = []
    seen_display = set()
    for k in subs + fuzzy:
        d = idx[k]["display"]
        if d in seen_display:
            continue
        seen_display.add(d)
        out.append({"display": d, "ra_deg": idx[k]["ra_deg"],
                    "dec_deg": idx[k]["dec_deg"], "kind": idx[k]["kind"]})
        if len(out) >= limit:
            break
    return out


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
