"""
Multi-year seeing hindcast: GOWC physics vs measured DIMM/MASS at Paranal.

Uses Open-Meteo's HISTORICAL FORECAST API (distinct from the ERA5 /v1/archive,
which serves no pressure levels, and from the live forecast API, which retains
them only ~12 days). The historical-forecast endpoint archives pressure levels
from 2021 onward, overlapping the full ESO ASM DIMM/MASS archive (2025-01 ..
2026-08 here) -- turning the earlier N=61 indication into thousands of nights.

Caveat (stated in the paper): this archive is high-resolution forecast output,
not reanalysis, so it lacks ERA5's long-term homogeneity as models evolve. For a
rank-correlation study over ~20 months that is a minor issue.

Statistics done right (per the round-3 review):
  * hourly DIMM/MASS autocorrelate over 1-3 h, so hourly samples are NOT
    independent. We reduce to NIGHTLY medians (one value per site per night) for
    the headline rank correlation -- the honest effective N.
  * Spearman rho with a Fisher-z 95% CI on the nightly series.
  * A moving-block bootstrap CI as a cross-check that does not assume the
    nightly reduction fully removes autocorrelation.
  * We report both the hourly rho (inflated N) and the nightly rho (honest N)
    so the difference is visible.

Run:
    python tests/hindcast_multiyear.py
"""
import os
import csv
import json
import math
import statistics
import random
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
PVARS = [f"{q}_{p}hPa" for p in (850, 700, 600, 500, 250)
         for q in ("temperature", "geopotential_height", "wind_speed")]
PVARS += ["relative_humidity_850hPa", "wind_speed_10m"]
# 250 hPa has no temp/geopot need here; drop the unused ones the API rejects.
PVARS = [v for v in PVARS if not (v.startswith(("temperature_250", "geopotential_height_250")))]


def fetch_profile(site):
    cache = os.path.join(HERE, f"hfa_{site.replace(' ', '')}.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    cfg = SITES[site]
    r = requests.get(HFA, params={
        "latitude": cfg["lat"], "longitude": cfg["lon"],
        "start_date": START, "end_date": END,
        "hourly": ",".join(PVARS), "timezone": "UTC",
    }, timeout=180)
    r.raise_for_status()
    h = r.json()["hourly"]
    json.dump(h, open(cache, "w"))
    return h


def gowc_hourly(site):
    """GOWC per-level seeing per hour -> {datetime: seeing}."""
    h = fetch_profile(site)
    alt = SITES[site]["alt"]
    out = {}
    for i, ts in enumerate(h["time"]):
        def g(k):
            v = h.get(k, [])
            return v[i] if i < len(v) else None
        levels = [{"p": float(p), "t": g(f"temperature_{p}hPa"),
                   "z": g(f"geopotential_height_{p}hPa"),
                   "w": g(f"wind_speed_{p}hPa")} for p in (850, 700, 600, 500, 250)]
        t8, t5 = g("temperature_850hPa"), g("temperature_500hPa")
        z8, z5 = g("geopotential_height_850hPa"), g("geopotential_height_500hPa")
        if None in (t8, t5, z8, z5):
            continue
        s = a.calculate_seeing_tatarski(
            t8, t5, z8, z5,
            wind_850_ms=g("wind_speed_850hPa"), wind_500_ms=g("wind_speed_500hPa"),
            wind_250_ms=g("wind_speed_250hPa"),
            airmass=1.0, surface_wind_ms=(g("wind_speed_10m") or 0) / 3.6,
            humidity_pct=g("relative_humidity_850hPa"), altitude_m=alt,
            levels=levels,
            # This hindcast runs on the Historical Forecast API, whose gradients
            # differ from the live Forecast API, so use the HFA-fitted constant.
            cn2_scale=a._MULTILEVEL_CN2_SCALE_HFA)
        if s is not None:
            out[datetime.fromisoformat(ts[:19])] = s
    return out


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


def nightly_medians(hourly):
    """Collapse an {hour: value} dict to {date: median-over-night}. A 'night'
    is keyed by the local date at UTC-4 (Chile), so an observing night maps to
    one calendar date."""
    by_night = {}
    for t, v in hourly.items():
        night = (t - timedelta(hours=4)).date()   # Chile local; groups a night
        by_night.setdefault(night, []).append(v)
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


def analyse(site):
    print(f"\n{'='*60}\n{site}\n{'='*60}")
    pred = gowc_hourly(site)
    dimm = measured_hourly(SITES[site]["dimm"], "seeing")

    # ---- hourly (inflated N) ----
    ch = sorted(set(pred) & set(dimm))
    ph = [pred[t] for t in ch]
    dh = [dimm[t] for t in ch]
    rho_h = spearman(ph, dh)
    print(f"\nHOURLY (autocorrelated, inflated N):")
    print(f"  N={len(ch)}  rho(GOWC,DIMM)={rho_h:+.3f}  "
          f"CI{fisher_ci(rho_h, len(ch))}")

    # ---- nightly medians (honest N) ----
    pn = nightly_medians(pred)
    dn = nightly_medians(dimm)
    cn = sorted(set(pn) & set(dn))
    pv = [pn[d] for d in cn]
    dv = [dn[d] for d in cn]
    rho_n = spearman(pv, dv)
    lo, hi = fisher_ci(rho_n, len(cn))
    bpairs = [(d, pn[d], dn[d]) for d in cn]
    blo, bhi = block_bootstrap_ci(bpairs)
    print(f"\nNIGHTLY MEDIANS (honest N):")
    print(f"  nights N={len(cn)}")
    print(f"  rho(GOWC,DIMM) = {rho_n:+.3f}")
    print(f"  Fisher 95% CI  = [{lo:+.3f}, {hi:+.3f}]")
    print(f"  block-boot CI  = [{blo:+.3f}, {bhi:+.3f}]")
    med_g = statistics.median(pv)
    med_d = statistics.median(dv)
    print(f"  median GOWC={med_g:.2f}\"  median DIMM={med_d:.2f}\"  "
          f"bias={med_g/med_d:.2f}x")

    # ---- MASS comparison if available ----
    if SITES[site]["mass"] and os.path.exists(SITES[site]["mass"]):
        mass = measured_hourly(SITES[site]["mass"], "free atmosphere")
        mn = nightly_medians(mass)
        cm = sorted(set(pn) & set(mn))
        if len(cm) > 10:
            rho_m = spearman([pn[d] for d in cm], [mn[d] for d in cm])
            lo2, hi2 = fisher_ci(rho_m, len(cm))
            print(f"\n  vs MASS free-atm (nightly): N={len(cm)}  "
                  f"rho={rho_m:+.3f}  CI[{lo2:+.3f},{hi2:+.3f}]")

    return {"site": site, "nights": len(cn), "rho_nightly": rho_n,
            "ci": (lo, hi), "bias": med_g / med_d}


def wind_test(site):
    """Re-test the upper-wind vs free-atmosphere-seeing correlation on the full
    baseline (round-3 Blocker 4). Uses DIMM as the seeing proxy where MASS is
    absent; nightly medians."""
    h = fetch_profile(site)
    w250 = {}
    for i, ts in enumerate(h["time"]):
        v = h.get("wind_speed_250hPa", [])
        if i < len(v) and v[i] is not None:
            w250[datetime.fromisoformat(ts[:19])] = v[i]
    dimm = measured_hourly(SITES[site]["dimm"], "seeing")
    wn = nightly_medians(w250)
    dn = nightly_medians(dimm)
    c = sorted(set(wn) & set(dn))
    if len(c) > 10:
        rho = spearman([wn[d] for d in c], [dn[d] for d in c])
        lo, hi = fisher_ci(rho, len(c))
        print(f"\n  WIND TEST ({site}): rho(250hPa wind, DIMM total) = {rho:+.3f}  "
              f"CI[{lo:+.3f},{hi:+.3f}]  N={len(c)} nights")
        print(f"    (literature expects POSITIVE: strong jet -> worse free-atm seeing)")


if __name__ == "__main__":
    random.seed(1)
    for s in SITES:
        analyse(s)
        wind_test(s)
