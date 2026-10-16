"""
Multi-year seeing hindcast: GOWC physics vs measured DIMM/MASS at Paranal and
La Silla.

Uses Open-Meteo's HISTORICAL FORECAST API (distinct from the ERA5 /v1/archive,
which serves no pressure levels, and from the live forecast API, which retains
them only ~12 days). The historical-forecast endpoint archives pressure levels
from 2021 onward, overlapping the ESO ASM DIMM/MASS archive (2025-01 .. 2026-08).

Conventions (Oct 2026 revision, after an external code review):
  * UNITS. The archive returns wind in km/h unless asked otherwise, and the
    cached hfa_*.json files are in km/h. Every wind field -- surface AND
    pressure-level -- is converted to m/s on load, matching the live fetch
    (fetch_weather.py requests m/s). An earlier version converted only the 10 m
    wind, which inflated the Dewan shear 3.6x and biased the calibration.
  * NIGHTS. An observing night is keyed noon-to-noon in Chilean local time
    (UTC-4): night = (t_utc - 16 h).date(), so the hours of one night share a
    key. The model is sampled ONLY at the hours the instrument measured, so the
    nightly model median never includes daytime hours.
  * MASS is compared with the model's FREE-ATMOSPHERE seeing alone.
  * hourly samples autocorrelate over 1-3 h, so the headline statistics use one
    median per night, with Fisher-z and moving-block-bootstrap CIs.

Run:
    python tests/hindcast_multiyear.py
"""
import os
import csv
import json
import math
import statistics
import random
from collections import defaultdict
from datetime import datetime, timedelta

import requests

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import atmospheric as a   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HFA = "https://historical-forecast-api.open-meteo.com/v1/forecast"

SITES = {
    "Paranal": {
        "lat": -24.6275, "lon": -70.4044, "alt": 2635.0,
        "dimm": os.path.join(os.path.dirname(HERE), "dimm_measured.csv"),
        "mass": os.path.join(HERE, "mass_paranal_2026-05_08.csv"),  # MASS overlap
    },
    "La Silla": {
        "lat": -29.2584, "lon": -70.7331, "alt": 2400.0,
        "dimm": os.path.join(HERE, "dimm_measured_Lasilla.csv"),
        "mass": None,
    },
}

START, END = "2025-01-01", "2026-08-28"
LEVELS = (850, 700, 600, 500)          # the levels the live model integrates
PVARS = [f"{q}_{p}hPa" for p in LEVELS
         for q in ("temperature", "geopotential_height", "wind_speed")]
PVARS += ["wind_speed_250hPa", "relative_humidity_850hPa", "wind_speed_10m"]
KMH_PER_MS = 3.6
NIGHT_OFFSET_H = 16                    # UTC-4 local, keyed noon to noon


def fetch_profile(site):
    """Hourly Historical-Forecast fields for a site, with ALL winds in m/s.
    The cache (and a fresh download, which omits wind_speed_unit) is km/h."""
    cache = os.path.join(HERE, f"hfa_{site.replace(' ', '')}.json")
    if os.path.exists(cache):
        h = json.load(open(cache))
    else:
        cfg = SITES[site]
        r = requests.get(HFA, params={
            "latitude": cfg["lat"], "longitude": cfg["lon"],
            "start_date": START, "end_date": END,
            "hourly": ",".join(PVARS), "timezone": "UTC",
        }, timeout=180)
        r.raise_for_status()
        h = r.json()["hourly"]
        json.dump(h, open(cache, "w"))
    return {k: ([None if v is None else v / KMH_PER_MS for v in vals]
                if k.startswith("wind_speed_") else vals)
            for k, vals in h.items()}


def _hours(site):
    """Yield (datetime, getter) for every archived hour."""
    h = fetch_profile(site)
    for i, ts in enumerate(h["time"]):
        def g(k, i=i):
            v = h.get(k, [])
            return v[i] if i < len(v) else None
        yield datetime.fromisoformat(ts[:19]), g


def _levels(g):
    return [{"p": float(p), "t": g(f"temperature_{p}hPa"),
             "z": g(f"geopotential_height_{p}hPa"), "w": g(f"wind_speed_{p}hPa")}
            for p in LEVELS
            if g(f"temperature_{p}hPa") is not None
            and g(f"geopotential_height_{p}hPa") is not None]


def gowc_hourly(site, cn2_scale=None, layer_thickness_m=None):
    """GOWC total seeing per hour (zenith) -> {datetime: arcsec}, exactly as the
    live model computes it (calculate_seeing_tatarski with the real levels)."""
    alt = SITES[site]["alt"]
    kw = {}
    if cn2_scale is not None:
        kw["cn2_scale"] = cn2_scale
    if layer_thickness_m is not None:
        kw["layer_thickness_m"] = layer_thickness_m
    out = {}
    for t, g in _hours(site):
        t8, t5 = g("temperature_850hPa"), g("temperature_500hPa")
        z8, z5 = g("geopotential_height_850hPa"), g("geopotential_height_500hPa")
        if None in (t8, t5, z8, z5):
            continue
        s = a.calculate_seeing_tatarski(
            t8, t5, z8, z5,
            wind_850_ms=g("wind_speed_850hPa"), wind_500_ms=g("wind_speed_500hPa"),
            wind_250_ms=g("wind_speed_250hPa"),
            airmass=1.0, surface_wind_ms=g("wind_speed_10m"),
            humidity_pct=g("relative_humidity_850hPa"), altitude_m=alt,
            levels=_levels(g), **kw)
        if s is not None:
            out[t] = s
    return out


def free_hourly(site, cn2_scale=None):
    """Free-atmosphere (per-level) seeing alone per hour."""
    alt = SITES[site]["alt"]
    kw = {} if cn2_scale is None else {"cn2_scale": cn2_scale}
    out = {}
    for t, g in _hours(site):
        f = a.free_atmosphere_seeing_multilevel(_levels(g), alt, airmass=1.0, **kw)
        if f is not None:
            out[t] = f
    return out


def surface_wind_hourly(site):
    return {t: g("wind_speed_10m") for t, g in _hours(site)
            if g("wind_speed_10m") is not None}


def measured_hourly(path, value_key):
    """Measured seeing -> {hour: mean}. Auto-detects columns."""
    bins = {}
    with open(path, newline="") as f:
        header = None
        for row in csv.reader(f):
            if not row or all(not c.strip() for c in row) or row[0].startswith("#"):
                continue
            if header is None:
                header = [c.lower() for c in row]
                ti = next(i for i, c in enumerate(header) if "date" in c or "time" in c)
                vi = next(i for i, c in enumerate(header) if value_key in c)
                continue
            try:
                t = datetime.fromisoformat(row[ti][:19]).replace(minute=0, second=0)
                v = float(row[vi])
            except (ValueError, IndexError):
                continue
            if v > 0:
                bins.setdefault(t, []).append(v)
    return {t: statistics.mean(v) for t, v in bins.items()}


def _ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(x, y):
    return statistics.correlation(_ranks(x), _ranks(y))


def fisher_ci(rho, n, z=1.96):
    if n <= 3:
        return (float("nan"), float("nan"))
    zr = 0.5 * math.log((1 + rho) / (1 - rho))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = zr - z * se, zr + z * se
    return (math.tanh(lo), math.tanh(hi))


def night_of(t):
    """Observing-night key: noon-to-noon in Chilean local time (UTC-4)."""
    return (t - timedelta(hours=NIGHT_OFFSET_H)).date()


def nightly_medians(hourly, hours=None):
    """Collapse {hour: value} to {night: median}. If `hours` is given, only
    those hours are used -- pass the instrument's hours so the model is sampled
    when, and only when, the instrument measured."""
    by_night = {}
    for t, v in hourly.items():
        if hours is not None and t not in hours:
            continue
        by_night.setdefault(night_of(t), []).append(v)
    return {d: statistics.median(vs) for d, vs in by_night.items()}


def block_bootstrap_ci(pairs, n_boot=2000, block=5):
    """Moving-block bootstrap CI for Spearman rho on time-ordered nightly pairs."""
    pairs = sorted(pairs)                        # by date
    xs = [p[1] for p in pairs]
    ys = [p[2] for p in pairs]
    n = len(xs)
    if n < 10:
        return (float("nan"), float("nan"))
    nblocks = math.ceil(n / block)
    rhos = []
    for _ in range(n_boot):
        bx, by = [], []
        for _ in range(nblocks):
            s = random.randint(0, n - block)
            bx += xs[s:s + block]
            by += ys[s:s + block]
        bx, by = bx[:n], by[:n]
        try:
            rhos.append(spearman(bx, by))
        except Exception:
            pass
    rhos.sort()
    return (rhos[int(0.025 * len(rhos))], rhos[int(0.975 * len(rhos))])


def calibrate():
    """Paranal calibration of the free-atmosphere constants against MASS:
    the per-level scale C and the two-level fallback thickness. Each is set so
    the model's free-atmosphere median over the MASS hours equals the MASS
    median over the same hours (eps scales as C^(3/5) and as dh^(3/5))."""
    mass = measured_hourly(SITES["Paranal"]["mass"], "free atmosphere")
    f1 = free_hourly("Paranal", cn2_scale=1.0)
    hrs = [t for t in f1 if t in mass]
    m_med = statistics.median(mass[t] for t in hrs)
    c_needed = (m_med / statistics.median(f1[t] for t in hrs)) ** (5 / 3)

    # two-level fallback: free-atm part of calculate_seeing_tatarski(levels=None)
    fb = {}
    for t, g in _hours("Paranal"):
        if t not in mass:
            continue
        t8, t5 = g("temperature_850hPa"), g("temperature_500hPa")
        z8, z5 = g("geopotential_height_850hPa"), g("geopotential_height_500hPa")
        if None in (t8, t5, z8, z5):
            continue
        s = a.calculate_seeing_tatarski(
            t8, t5, z8, z5, wind_850_ms=g("wind_speed_850hPa"),
            wind_500_ms=g("wind_speed_500hPa"), airmass=1.0,
            surface_wind_ms=g("wind_speed_10m"), altitude_m=2635.0,
            layer_thickness_m=1000.0, levels=None, components=True)
        if s is not None:
            fb[t] = s["free"]
    dh_needed = 1000.0 * (m_med / statistics.median(fb.values())) ** (5 / 3)

    print(f"CALIBRATION (Paranal, {len(hrs)} MASS-matched hours)")
    print(f"  MASS free-atmosphere median     = {m_med:.3f}\"")
    print(f"  per-level scale C needed        = {c_needed:.3f}   "
          f"(code: {a._MULTILEVEL_CN2_SCALE}; c_eff = {a._C_TATARSKI * c_needed:.2f})")
    print(f"  two-level fallback thickness    = {dh_needed:.0f} m")
    return c_needed, dh_needed


def analyse(site):
    print(f"\n{'='*60}\n{site}\n{'='*60}")
    pred = gowc_hourly(site)
    dimm = measured_hourly(SITES[site]["dimm"], "seeing")

    # ---- hourly (inflated N) ----
    ch = sorted(set(pred) & set(dimm))
    rho_h = spearman([pred[t] for t in ch], [dimm[t] for t in ch])
    print(f"\nHOURLY (autocorrelated, inflated N):")
    print(f"  N={len(ch)}  rho(GOWC,DIMM)={rho_h:+.3f}")

    # ---- nightly medians (honest N), model sampled at DIMM hours ----
    pn = nightly_medians(pred, hours=dimm)
    dn = nightly_medians(dimm)
    cn = sorted(set(pn) & set(dn))
    pv = [pn[d] for d in cn]
    dv = [dn[d] for d in cn]
    rho_n = spearman(pv, dv)
    lo, hi = fisher_ci(rho_n, len(cn))
    blo, bhi = block_bootstrap_ci([(d, pn[d], dn[d]) for d in cn])
    print(f"\nNIGHTLY MEDIANS (honest N):")
    print(f"  nights N={len(cn)}  ({cn[0]} .. {cn[-1]})")
    print(f"  rho(GOWC,DIMM) = {rho_n:+.3f}")
    print(f"  Fisher 95% CI  = [{lo:+.3f}, {hi:+.3f}]")
    print(f"  block-boot CI  = [{blo:+.3f}, {bhi:+.3f}]")
    med_g, med_d = statistics.median(pv), statistics.median(dv)
    print(f"  median GOWC={med_g:.2f}\"  median DIMM={med_d:.2f}\"  "
          f"bias={med_g/med_d:.2f}x")

    # ---- MASS: free-atmosphere model vs free-atmosphere measurement ----
    if SITES[site]["mass"] and os.path.exists(SITES[site]["mass"]):
        mass = measured_hourly(SITES[site]["mass"], "free atmosphere")
        fn = nightly_medians(free_hourly(site), hours=mass)
        mn = nightly_medians(mass)
        cm = sorted(set(fn) & set(mn))
        if len(cm) > 10:
            rho_m = spearman([fn[d] for d in cm], [mn[d] for d in cm])
            lo2, hi2 = fisher_ci(rho_m, len(cm))
            print(f"\n  eps_free vs MASS (nightly): N={len(cm)}  "
                  f"rho={rho_m:+.3f}  CI[{lo2:+.3f},{hi2:+.3f}]")
            print(f"  median eps_free={statistics.median(fn[d] for d in cm):.2f}\"  "
                  f"median MASS={statistics.median(mn[d] for d in cm):.2f}\"")

    return {"site": site, "nights": len(cn), "rho_nightly": rho_n,
            "ci": (lo, hi), "bias": med_g / med_d}


def wind_test(site):
    """250 hPa (jet) wind vs DIMM total seeing, nightly, at DIMM hours."""
    w250 = {t: g("wind_speed_250hPa") for t, g in _hours(site)
            if g("wind_speed_250hPa") is not None}
    dimm = measured_hourly(SITES[site]["dimm"], "seeing")
    wn, dn = nightly_medians(w250, hours=dimm), nightly_medians(dimm)
    c = sorted(set(wn) & set(dn))
    if len(c) > 10:
        rho = spearman([wn[d] for d in c], [dn[d] for d in c])
        lo, hi = fisher_ci(rho, len(c))
        print(f"\n  WIND TEST ({site}): rho(250hPa wind, DIMM total) = {rho:+.3f}  "
              f"CI[{lo:+.3f},{hi:+.3f}]  N={len(c)} nights")


def baselines(site):
    """GOWC against the predictors an observer already has: a monthly-
    deseasonalised correlation, persistence (last night's measured DIMM), and
    surface wind alone. Nightly medians at DIMM hours throughout."""
    pred = gowc_hourly(site)
    dimm = measured_hourly(SITES[site]["dimm"], "seeing")
    pn, dn = nightly_medians(pred, hours=dimm), nightly_medians(dimm)
    cn = sorted(set(pn) & set(dn))
    print(f"\n  BASELINES ({site}, N={len(cn)} nights):")
    print(f"  GOWC vs DIMM           rho = "
          f"{spearman([pn[d] for d in cn], [dn[d] for d in cn]):+.3f}")

    def deseason(series):
        bym = defaultdict(list)
        for d in cn:
            bym[d.month].append(series[d])
        med = {m: statistics.median(v) for m, v in bym.items()}
        return {d: series[d] - med[d.month] for d in cn}
    pa, da = deseason(pn), deseason(dn)
    print(f"  GOWC vs DIMM (deseas.) rho = "
          f"{spearman([pa[d] for d in cn], [da[d] for d in cn]):+.3f}")

    pp = [(dn[cn[i - 1]], dn[cn[i]]) for i in range(1, len(cn))
          if (cn[i] - cn[i - 1]).days == 1]
    if pp:
        print(f"  persistence (DIMM t-1) rho = "
              f"{spearman([p[0] for p in pp], [p[1] for p in pp]):+.3f}  (N={len(pp)})")

    swn = nightly_medians(surface_wind_hourly(site), hours=dimm)
    cw = [d for d in cn if d in swn]
    if len(cw) > 10:
        print(f"  surface wind alone     rho = "
              f"{spearman([swn[d] for d in cw], [dn[d] for d in cw]):+.3f}  (N={len(cw)})")


if __name__ == "__main__":
    random.seed(1)
    calibrate()
    for s in SITES:
        analyse(s)
        wind_test(s)
        baselines(s)
