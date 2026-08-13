"""
Transient & target-class follow-up support for GOWC.

Design goal: target CLASSES are data-driven, not hardcoded. Everything the
dashboard tab needs is derived from TARGET_CLASSES — a config mapping each
class to a behaviour MODE and a data source. Adding kilonovae, TDEs, etc.
later means adding a dict entry (and a fetcher), never editing the tab's
control flow.

Behaviour modes (how the class behaves observationally):
  - persistent : always present, watch for state changes (XRBs, AGN, pulsars…)
  - transient  : appears from nothing, needs fast response (SNe, GRBs, FRBs…)
  - triggered  : an external alert sends everyone looking (GW, neutrino)

Only neutron-star X-ray binaries carry live data in this first version.
Every other class resolves to the "coming soon" placeholder. Observability
(is it up tonight, airmass, which sites can see it, conditions) is layered
on top by reusing GOWC's existing ephem + airmass primitives — this module
adds an arbitrary RA/Dec path so any transient coordinate works, without
touching the existing OBJECTS-catalogue code.
"""
from __future__ import annotations

import math
import re
import urllib.request
from datetime import datetime, timezone, timedelta

import ephem

from airmass_calculator import (
    altitude_to_airmass,
    airmass_quality,
    extinction_magnitudes,
)


# ══════════════════════════════════════════════════════════════════
# Behaviour modes
# ══════════════════════════════════════════════════════════════════
MODE_PERSISTENT = "persistent"
MODE_TRANSIENT = "transient"
MODE_TRIGGERED = "triggered"

MODE_LABEL = {
    MODE_PERSISTENT: "Persistent but variable",
    MODE_TRANSIENT: "Sudden transient",
    MODE_TRIGGERED: "Triggered follow-up",
}

MODE_BLURB = {
    MODE_PERSISTENT: (
        "Always present — the science is in catching a *state change* "
        "(outburst, flare, mode switch). Monitor cadence matters more "
        "than reaction speed."
    ),
    MODE_TRANSIENT: (
        "Appears from nothing and fades. Value is in *fast response* — "
        "get on target within hours to days of discovery."
    ),
    MODE_TRIGGERED: (
        "An external observatory issues an alert and the whole community "
        "points at once, often at a large sky-localisation region."
    ),
}


# ══════════════════════════════════════════════════════════════════
# Target-class registry (the extensibility backbone)
#
# Each class entry:
#   mode        : one of the MODE_* constants
#   group       : selector grouping shown in the UI
#   source      : callable() -> list[target dicts], or None for "coming soon"
#   description : one-line science summary for the tab
#
# A target dict (from a source callable) uses:
#   name, ra_deg, dec_deg, and optional: alt_name, kind, flux, updated,
#   alert_level, comment, catalog (True for known/curated, False for a
#   live alert).
# ══════════════════════════════════════════════════════════════════
def _merge_catalog_with_maxi(catalog, extra_alert_keywords=None):
    """Curated catalogue enriched with live MAXI outburst alerts.

    A MAXI alert is attached to a catalogue target when the alert comment
    names it (by name or alt_name). Alerts that match no catalogue target
    are surfaced as their own uncatalogued targets *only* when their
    comment matches `extra_alert_keywords` — this keeps, e.g., the BH-XRB
    class from absorbing every unrelated NS alert. Pass None to surface
    all unmatched alerts (the NS-XRB behaviour).
    """
    targets = [dict(t) for t in catalog]   # copy so the module-level catalogue
                                           # is never mutated across reruns
    alerts = fetch_maxi_xrb_alerts()
    by_name = {t["name"].lower(): t for t in targets}
    for a in alerts:
        matched = None
        cl = (a.get("comment") or "").lower()
        for key, tgt in by_name.items():
            if key in cl or (tgt.get("alt_name")
                             and tgt["alt_name"].lower() in cl):
                matched = tgt
                break
        if matched:
            matched["alert_level"] = a.get("alert_level")
            matched["updated"] = a.get("updated")
            matched["comment"] = a.get("comment")
        elif extra_alert_keywords is None or any(
                k in cl for k in extra_alert_keywords):
            targets.append(a)
    return targets


def _ns_xray_binary_source():
    """NS-XRB catalogue + all live MAXI XRB alerts."""
    return _merge_catalog_with_maxi(NS_XRB_CATALOG, extra_alert_keywords=None)


def _bh_xray_binary_source():
    """BH-XRB catalogue + only BH-flavoured uncatalogued MAXI alerts."""
    return _merge_catalog_with_maxi(
        BH_XRB_CATALOG,
        extra_alert_keywords=("black hole", "black-hole", "bh ", "grs ",
                              "gx 339", "cyg x-1", "v404"))


TARGET_CLASSES = {
    # ── Compact objects (persistent but variable) ──────────────────
    "Neutron-star X-ray binaries (LMXB/HMXB)": {
        "mode": MODE_PERSISTENT,
        "group": "Compact objects",
        "source": _ns_xray_binary_source,
        "description": (
            "Accreting neutron stars in binaries — Type-I bursts, outbursts "
            "and state transitions. Live outburst alerts from MAXI/RIKEN."
        ),
    },
    "Black-hole X-ray binaries": {
        "mode": MODE_PERSISTENT,
        "group": "Compact objects",
        "source": _bh_xray_binary_source,
        "description": (
            "Accreting stellar-mass black holes — hard/soft state cycles and "
            "outbursts. Curated catalogue plus live BH-flavoured MAXI alerts."
        ),
    },
    "Cataclysmic variables": {
        "mode": MODE_PERSISTENT, "group": "Compact objects", "source": None,
        "description": "White-dwarf accretors; dwarf-nova outbursts.",
    },
    "Magnetars": {
        "mode": MODE_PERSISTENT, "group": "Compact objects", "source": None,
        "description": "Ultra-magnetic neutron stars; X-ray/soft-gamma bursts.",
    },
    "Pulsars": {
        "mode": MODE_PERSISTENT, "group": "Compact objects", "source": None,
        "description": "Rotation-powered neutron stars.",
    },
    "Millisecond / transitional pulsars": {
        "mode": MODE_PERSISTENT, "group": "Compact objects", "source": None,
        "description": "Recycled pulsars switching between radio and accretion.",
    },

    # ── Explosive transients (sudden) ──────────────────────────────
    "Supernovae": {
        "mode": MODE_TRANSIENT, "group": "Explosive transients", "source": None,
        "description": "Core-collapse and Type-Ia stellar explosions.",
    },
    "Kilonovae": {
        "mode": MODE_TRANSIENT, "group": "Explosive transients", "source": None,
        "description": "Neutron-star merger ejecta; r-process light.",
    },
    "Tidal disruption events (TDEs)": {
        "mode": MODE_TRANSIENT, "group": "Explosive transients", "source": None,
        "description": "Stars shredded by supermassive black holes.",
    },
    "Gamma-ray bursts (GRBs)": {
        "mode": MODE_TRANSIENT, "group": "Explosive transients", "source": None,
        "description": "Most luminous explosions; afterglow follow-up.",
    },
    "Fast radio bursts (FRBs)": {
        "mode": MODE_TRANSIENT, "group": "Explosive transients", "source": None,
        "description": "Millisecond radio flashes; localisation follow-up.",
    },

    # ── Multi-messenger (triggered) ────────────────────────────────
    "Gravitational-wave events": {
        "mode": MODE_TRIGGERED, "group": "Multi-messenger", "source": None,
        "description": "LIGO/Virgo/KAGRA NS-NS, NS-BH, BH-BH mergers.",
    },
    "Neutrino events": {
        "mode": MODE_TRIGGERED, "group": "Multi-messenger", "source": None,
        "description": "IceCube high-energy neutrino alerts.",
    },

    # ── Active galaxies (persistent but variable) ──────────────────
    "AGN": {
        "mode": MODE_PERSISTENT, "group": "Active galaxies", "source": None,
        "description": "Accreting supermassive black holes.",
    },
    "Blazars": {
        "mode": MODE_PERSISTENT, "group": "Active galaxies", "source": None,
        "description": "Jet pointed at us; rapid multiwavelength flares.",
    },
    "Quasars": {
        "mode": MODE_PERSISTENT, "group": "Active galaxies", "source": None,
        "description": "Luminous distant AGN.",
    },

    # ── Periodic / variable (GOWC already covers these elsewhere) ──
    "Variable stars (Cepheids, RR Lyrae, Miras)": {
        "mode": MODE_PERSISTENT, "group": "Periodic / variable", "source": None,
        "description": "Pulsating standard candles — see Object Visibility.",
    },
    "Eclipsing binaries": {
        "mode": MODE_PERSISTENT, "group": "Periodic / variable", "source": None,
        "description": "Periodic dimming — see Object Visibility.",
    },
    "Exoplanet transits": {
        "mode": MODE_PERSISTENT, "group": "Periodic / variable", "source": None,
        "description": "Host-star dips — see Object Visibility.",
    },
}


def classes_by_group():
    """Return {group: [class_name, ...]} preserving registry order."""
    out = {}
    for name, cfg in TARGET_CLASSES.items():
        out.setdefault(cfg["group"], []).append(name)
    return out


def class_has_live_data(class_name):
    cfg = TARGET_CLASSES.get(class_name)
    return bool(cfg and cfg.get("source"))


def get_targets(class_name):
    """Return the target list for a class, or [] if it has no live source."""
    cfg = TARGET_CLASSES.get(class_name)
    if not cfg or not cfg.get("source"):
        return []
    try:
        return cfg["source"]() or []
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════
# Curated neutron-star X-ray binary catalogue
# Coordinates are J2000 decimal degrees. Small, well-known set — enough
# to make the observability layer useful; extend freely.
# ══════════════════════════════════════════════════════════════════
NS_XRB_CATALOG = [
    {"name": "Sco X-1", "alt_name": "V818 Sco", "ra_deg": 244.979, "dec_deg": -15.640,
     "kind": "LMXB", "catalog": True,
     "comment": "Brightest persistent X-ray source in the sky."},
    {"name": "GS 1826-238", "alt_name": "Ginga 1826", "ra_deg": 277.368, "dec_deg": -23.797,
     "kind": "LMXB (burster)", "catalog": True,
     "comment": "The 'clocked burster' — quasi-periodic Type-I bursts."},
    {"name": "Aql X-1", "alt_name": "V1333 Aql", "ra_deg": 287.817, "dec_deg": 0.585,
     "kind": "LMXB (transient)", "catalog": True,
     "comment": "Recurrent transient; frequent outbursts."},
    {"name": "Cen X-3", "alt_name": "V779 Cen", "ra_deg": 170.313, "dec_deg": -60.624,
     "kind": "HMXB (pulsar)", "catalog": True,
     "comment": "Accreting X-ray pulsar in a high-mass binary."},
    {"name": "Her X-1", "alt_name": "HZ Her", "ra_deg": 254.457, "dec_deg": 35.342,
     "kind": "LMXB (pulsar)", "catalog": True,
     "comment": "1.24 s accreting pulsar; 35-day super-orbital cycle."},
    {"name": "4U 1608-52", "alt_name": "QX Nor", "ra_deg": 243.179, "dec_deg": -52.423,
     "kind": "LMXB (transient burster)", "catalog": True,
     "comment": "Transient atoll source; thermonuclear bursts."},
    {"name": "GX 339-4", "alt_name": "V821 Ara", "ra_deg": 255.706, "dec_deg": -48.790,
     "kind": "LMXB", "catalog": True,
     "comment": "Well-studied recurrent transient (BH candidate historically)."},
    {"name": "Cyg X-2", "alt_name": "V1341 Cyg", "ra_deg": 326.171, "dec_deg": 38.322,
     "kind": "LMXB (Z-source)", "catalog": True,
     "comment": "Bright persistent Z-source."},
    {"name": "4U 1728-34", "alt_name": "GX 354-0", "ra_deg": 262.990, "dec_deg": -33.835,
     "kind": "LMXB (burster)", "catalog": True,
     "comment": "Frequent Type-I X-ray bursts; kHz QPOs."},
    {"name": "SAX J1808.4-3658", "alt_name": "V4580 Sgr", "ra_deg": 272.115, "dec_deg": -36.979,
     "kind": "LMXB (AMXP)", "catalog": True,
     "comment": "First accreting millisecond X-ray pulsar discovered."},
]


# ══════════════════════════════════════════════════════════════════
# Curated black-hole X-ray binary catalogue (J2000 decimal degrees).
# Well-known dynamically-confirmed or strong-candidate BH binaries.
# ══════════════════════════════════════════════════════════════════
BH_XRB_CATALOG = [
    {"name": "Cyg X-1", "alt_name": "V1357 Cyg", "ra_deg": 299.590, "dec_deg": 35.202,
     "kind": "HMXB (persistent BH)", "catalog": True,
     "comment": "First strong stellar black-hole candidate; ~21 M☉."},
    {"name": "GRS 1915+105", "alt_name": "V1487 Aql", "ra_deg": 288.798, "dec_deg": 10.946,
     "kind": "LMXB (microquasar)", "catalog": True,
     "comment": "Superluminal jets; long-lived outburst."},
    {"name": "GX 339-4", "alt_name": "V821 Ara", "ra_deg": 255.706, "dec_deg": -48.790,
     "kind": "LMXB (transient BH)", "catalog": True,
     "comment": "Recurrent transient; textbook hard/soft state cycles."},
    {"name": "V404 Cyg", "alt_name": "GS 2023+338", "ra_deg": 306.016, "dec_deg": 33.867,
     "kind": "LMXB (transient BH)", "catalog": True,
     "comment": "Nearby (~2.4 kpc); dramatic 2015 outburst."},
    {"name": "GRO J1655-40", "alt_name": "V1033 Sco", "ra_deg": 253.500, "dec_deg": -39.846,
     "kind": "LMXB (microquasar)", "catalog": True,
     "comment": "Superluminal jets; ~6.3 M☉ black hole."},
    {"name": "MAXI J1820+070", "alt_name": "ASASSN-18ey", "ra_deg": 275.091, "dec_deg": 7.185,
     "kind": "LMXB (transient BH)", "catalog": True,
     "comment": "Bright 2018 outburst; well-studied reverberation."},
    {"name": "GS 1354-64", "alt_name": "BW Cir", "ra_deg": 209.552, "dec_deg": -64.744,
     "kind": "LMXB (transient BH)", "catalog": True,
     "comment": "Recurrent transient black-hole binary."},
    {"name": "4U 1543-47", "alt_name": "IL Lup", "ra_deg": 236.788, "dec_deg": -47.669,
     "kind": "LMXB (transient BH)", "catalog": True,
     "comment": "Low-inclination transient; fast-rise outbursts."},
    {"name": "XTE J1550-564", "alt_name": "V381 Nor", "ra_deg": 237.744, "dec_deg": -56.476,
     "kind": "LMXB (transient BH)", "catalog": True,
     "comment": "Relativistic jets seen in 1998 outburst."},
    {"name": "Cyg X-3", "alt_name": "V1521 Cyg", "ra_deg": 308.107, "dec_deg": 40.958,
     "kind": "HMXB (jet source)", "catalog": True,
     "comment": "Compact object debated; strong radio flares."},
]


# ══════════════════════════════════════════════════════════════════
# Live alert feed: MAXI / RIKEN nova-alert page
# ══════════════════════════════════════════════════════════════════
_MAXI_URL = "http://maxi.riken.jp/alert/novae/"
_MAXI_TIMEOUT = 20


def fetch_maxi_xrb_alerts(max_age_days=120, limit=40):
    """Recent X-ray-binary-flavoured alerts from the MAXI novae page.

    Best-effort and network-tolerant: returns [] on any failure so the
    tab never breaks. Rows on the page are (ID, image, date, "(ra, dec)",
    comment); we keep recent rows whose comment reads like an XRB/transient
    rather than a known optical nova.
    """
    try:
        req = urllib.request.Request(_MAXI_URL, headers={"User-Agent": "GOWC/1.0"})
        html = urllib.request.urlopen(req, timeout=_MAXI_TIMEOUT).read()
        html = html.decode("utf-8", "replace")
    except Exception:
        return []

    m = re.search(r'<table[^>]*class="list".*?</table>', html, re.S | re.I)
    table = m.group(0) if m else ""
    rows = re.findall(r"<tr.*?</tr>", table, re.S | re.I)

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=max_age_days)
    out = []
    for r in rows:
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<td.*?</td>", r, re.S | re.I)]
        if len(cells) < 5:
            continue
        raw_id, _img, date_s, radec_s, comment = cells[:5]

        # Alert level from the ID cell, e.g. "… (Alert)" / "… (Warning)".
        lvl = None
        lm = re.search(r"\((Alert|Warning)\)", raw_id, re.I)
        if lm:
            lvl = lm.group(1).title()

        # Parse timestamp (ISO-ish); skip rows we can't date or that are old.
        dt = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_s.strip(), fmt)
                break
            except ValueError:
                continue
        if dt is None or dt < cutoff:
            continue

        cm = re.match(r"\(?\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)?", radec_s)
        if not cm:
            continue
        try:
            ra_deg = float(cm.group(1))
            dec_deg = float(cm.group(2))
        except ValueError:
            continue

        # Keep XRB / transient-flavoured alerts; drop pure optical novae.
        low = comment.lower()
        looks_xrb = any(k in low for k in
                        ("xrb", "x-ray", "maxi j", "transient", "burst", "gx ",
                         "4u ", "sax", "igr", "swift j", "aql", "sco x"))
        if not looks_xrb:
            continue

        name = comment.strip() or f"MAXI alert {date_s}"
        out.append({
            "name": name[:60],
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
            "kind": "MAXI alert",
            "catalog": False,
            "alert_level": lvl,
            "updated": dt.strftime("%Y-%m-%d %H:%M UTC"),
            "comment": comment,
        })

    # Most recent first.
    out.sort(key=lambda a: a.get("updated") or "", reverse=True)
    return out[:limit]


# ══════════════════════════════════════════════════════════════════
# Observability by arbitrary RA/Dec
# Reuses GOWC's airmass + extinction primitives; adds the RA/Dec path
# that the OBJECTS-catalogue functions don't expose.
# ══════════════════════════════════════════════════════════════════
def _observer(lat, lon, alt_m, when):
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.long = str(lon)
    obs.elevation = float(alt_m or 0)
    obs.pressure = 0
    obs.date = when.strftime("%Y/%m/%d %H:%M:%S")
    return obs


def _fixed_body(ra_deg, dec_deg, observer):
    body = ephem.FixedBody()
    body._ra = ephem.degrees(str(ra_deg))
    body._dec = ephem.degrees(str(dec_deg))
    body.compute(observer)
    return body


def observability_at(ra_deg, dec_deg, lat, lon, alt_m=0, when=None,
                     min_alt=15):
    """Observability of a fixed RA/Dec from one site right now (or `when`)."""
    if when is None:
        when = datetime.now(timezone.utc).replace(tzinfo=None)
    obs = _observer(lat, lon, alt_m, when)
    body = _fixed_body(ra_deg, dec_deg, obs)

    alt_deg = math.degrees(float(body.alt))
    az_deg = math.degrees(float(body.az))
    airmass = altitude_to_airmass(alt_deg) if alt_deg > 0 else None
    ext = (extinction_magnitudes(airmass, altitude_m=alt_m)
           if airmass is not None else None)

    sun = ephem.Sun()
    sun.compute(obs)
    sun_alt = math.degrees(float(sun.alt))

    return {
        "altitude_deg": round(alt_deg, 1),
        "azimuth_deg": round(az_deg, 1),
        "airmass": airmass,
        "airmass_quality": airmass_quality(airmass),
        "extinction_mag": ext,
        "is_up": alt_deg >= min_alt,
        "sun_alt": round(sun_alt, 1),
        "is_dark": sun_alt < -18,
        "is_night": sun_alt < 0,
        "observable_now": alt_deg >= min_alt and sun_alt < 0,
    }


def airmass_curve_radec(ra_deg, dec_deg, lat, lon, alt_m=0,
                        when=None, hours=12):
    """Airmass every 30 min for `hours` from one site, for a fixed RA/Dec.

    Mirrors airmass_calculator.get_object_airmass_curve but for arbitrary
    coordinates instead of a named OBJECTS entry.
    """
    if when is None:
        when = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    for i in range(hours * 2):
        t = when + timedelta(minutes=i * 30)
        obs = _observer(lat, lon, alt_m, t)
        try:
            body = _fixed_body(ra_deg, dec_deg, obs)
            alt_deg = math.degrees(float(body.alt))
            airmass = altitude_to_airmass(alt_deg)
            sun = ephem.Sun()
            sun.compute(obs)
            sun_alt = math.degrees(float(sun.alt))
            out.append({
                "time": t.strftime("%H:%M"),
                "altitude": round(alt_deg, 1),
                "airmass": airmass,
                "is_dark": sun_alt < -18,
                "is_night": sun_alt < 0,
            })
        except Exception:
            continue
    return out


def sites_that_can_observe(ra_deg, dec_deg, observatories_df, when=None,
                           min_alt=15, dark_only=True):
    """Rank observatories that can see a fixed RA/Dec right now.

    Blends GOWC's weather/observation_score with the target's atmospheric
    transmission at each site — the same combination Object Visibility uses.
    """
    import pandas as pd

    rows = []
    for _, o in observatories_df.iterrows():
        try:
            r = observability_at(
                ra_deg, dec_deg,
                o["latitude"], o["longitude"],
                alt_m=o.get("altitude_m", 0) or 0,
                when=when, min_alt=min_alt,
            )
        except Exception:
            continue
        if not r["is_up"]:
            continue
        if dark_only and not r["is_night"]:
            continue

        ext = r["extinction_mag"]
        transmission = (10 ** (-ext / 2.5)) if ext is not None else 0.0
        weather = o.get("observation_score", 0) or 0
        rows.append({
            "observatory": o.get("observatory"),
            "country": o.get("country"),
            "weather_score": weather,
            "altitude_deg": r["altitude_deg"],
            "airmass": r["airmass"],
            "airmass_quality": r["airmass_quality"],
            "is_dark": r["is_dark"],
            "combined_score": round(weather * 0.6 + transmission * 100 * 0.4, 1),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("combined_score", ascending=False)
