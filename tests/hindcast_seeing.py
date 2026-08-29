"""
Reanalysis hindcast of GOWC seeing vs measured DIMM at Paranal (review 2.2).

The Open-Meteo *archive* (ERA5) API does not serve pressure-level fields, but the
*forecast* API with past_days serves 850/500/250 hPa profiles back ~92 days. That
window (2026-05-29 .. 2026-08-29) overlaps our downloaded ESO ASM DIMM+MASS
archive, so we can compute a genuine TIME-MATCHED comparison today rather than
waiting months for forward logging.

This is model-analysis (short-range forecast) profile data, not on-site
measurement, so the rank correlation is an UPPER BOUND on operational skill.

Outputs (per site, on time-matched hourly pairs):
  * Spearman rho (night-to-night ranking skill)
  * Pearson r
  * median bias (GOWC/DIMM)
  * RMS of log10(eps) after removing the median bias (scatter, bias-independent)

Run:
    python tests/hindcast_seeing.py
"""
import os
import csv
import json
import math
import statistics
from datetime import datetime

import requests

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from atmospheric import calculate_seeing_tatarski  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

SITES = {
    "Paranal": {
        "lat": -24.6275, "lon": -70.4044, "alt": 2635.0,
        "dimm": os.path.join(HERE, "dimm_paranal_2026-05_08.csv"),
    },
}

PROFILE_VARS = ("temperature_850hPa", "temperature_500hPa",
                "geopotential_height_850hPa", "geopotential_height_500hPa",
                "wind_speed_850hPa", "wind_speed_250hPa",
                "relative_humidity_850hPa", "wind_speed_10m")


def fetch_profile(site):
    """Hourly pressure-level profile for the past ~92 days (cached to JSON)."""
    cache = os.path.join(HERE, f"profile_{site}.json")
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    cfg = SITES[site]
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": cfg["lat"], "longitude": cfg["lon"],
        "hourly": ",".join(PROFILE_VARS),
        "past_days": 92, "forecast_days": 1, "timezone": "UTC",
    }, timeout=60)
    r.raise_for_status()
    data = r.json()["hourly"]
    with open(cache, "w") as f:
        json.dump(data, f)
    return data


def gowc_seeing_series(site):
    """Predicted zenith seeing per hour from the corrected physics.
    Returns {datetime(hour): seeing}."""
    h = fetch_profile(site)
    alt = SITES[site]["alt"]
    out = {}
    for i, tstr in enumerate(h["time"]):
        def g(k):
            v = h.get(k, [])
            return v[i] if i < len(v) else None
        t850, t500 = g("temperature_850hPa"), g("temperature_500hPa")
        z850, z500 = g("geopotential_height_850hPa"), g("geopotential_height_500hPa")
        if None in (t850, t500, z850, z500):
            continue
        seeing = calculate_seeing_tatarski(
            t850, t500, z850, z500,
            wind_850_ms=g("wind_speed_850hPa"), wind_250_ms=g("wind_speed_250hPa"),
            airmass=1.0,                       # zenith, to match DIMM normalisation
            surface_wind_ms=(g("wind_speed_10m") or 0) / 3.6,  # km/h -> m/s
            humidity_pct=g("relative_humidity_850hPa"),
            altitude_m=alt)
        if seeing is not None:
            out[datetime.fromisoformat(tstr[:19])] = seeing
    return out


def dimm_hourly(site):
    """Measured DIMM total seeing averaged into hourly bins."""
    path = SITES[site]["dimm"]
    bins = {}
    with open(path, newline="") as f:
        header = None
        for row in csv.reader(f):
            if not row or all(not c.strip() for c in row):
                continue
            if header is None:
                header = [c.lower() for c in row]
                ti = next(i for i, c in enumerate(header) if "date" in c)
                vi = next(i for i, c in enumerate(header) if "seeing" in c)
                continue
            try:
                ts = datetime.fromisoformat(row[ti][:19]).replace(
                    minute=0, second=0)
                val = float(row[vi])
            except (ValueError, IndexError):
                continue
            if val > 0:
                bins.setdefault(ts, []).append(val)
    return {t: statistics.mean(v) for t, v in bins.items()}


def _spearman(x, y):
    def ranks(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    return statistics.correlation(rx, ry)


def analyse(site):
    pred = gowc_seeing_series(site)
    meas = dimm_hourly(site)
    common = sorted(set(pred) & set(meas))
    if len(common) < 10:
        print(f"{site}: only {len(common)} matched hours — insufficient.")
        return
    p = [pred[t] for t in common]
    m = [meas[t] for t in common]

    rho = _spearman(p, m)
    r = statistics.correlation(p, m)
    ratios = [p[i] / m[i] for i in range(len(p)) if m[i] > 0]
    bias = statistics.median(ratios)
    # debiased RMS of log10(eps): remove median log-offset, then RMS
    logres = [math.log10(p[i] / bias) - math.log10(m[i])
              for i in range(len(p)) if m[i] > 0 and p[i] > 0]
    rms_log = (sum(e * e for e in logres) / len(logres)) ** 0.5

    print(f"\n  {site}: reanalysis hindcast vs measured DIMM")
    print("  " + "-" * 50)
    print(f"  matched hourly pairs      N = {len(common)}")
    print(f"  window                    {common[0].date()} .. {common[-1].date()}")
    print(f"  GOWC median seeing        {statistics.median(p):.2f}\"")
    print(f"  DIMM median seeing        {statistics.median(m):.2f}\"")
    print(f"  Spearman rho              {rho:+.3f}")
    print(f"  Pearson r                 {r:+.3f}")
    print(f"  median bias (GOWC/DIMM)   {bias:.2f}x")
    print(f"  debiased RMS(log10 eps)   {rms_log:.3f} dex  "
          f"(= x{10**rms_log:.2f} scatter)")
    print("  NOTE: profile is short-range analysis, not on-site measurement,")
    print("        so rho is an UPPER BOUND on operational forecast skill.")


if __name__ == "__main__":
    for s in SITES:
        analyse(s)
