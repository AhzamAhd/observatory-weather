"""
PWV validation: GOWC model-column PWV vs measured LHATPRO radiometer at Paranal.

Open-Meteo integrates the total column from the MODEL GRID CELL's terrain height
(its `elevation` field, 2617 m for the Paranal cell), so GOWC removes only the
residual water between that terrain and the telescope:
PWV(site) = PWV_model exp(-(h_site - h_model)/2000). This tests that against the
ESO LHATPRO radiometer over the full DIMM baseline -- a second quantitative
validation against a real instrument. The earlier sea-level scaling,
exp(-h_site/2000), which removed the sub-site column twice, is also printed as a
diagnostic (paper S4.2).

Model column comes from the Historical Forecast API (total_column_integrated_
water_vapour); measured PWV from the ESO ASM LHATPRO archive (mm, last CSV column).
Both reduced to nightly medians and correlated; bias and scatter reported.

Run:  python tests/validate_pwv_lhatpro.py
"""
import os
import csv
import json
import math
import statistics
from datetime import datetime, timedelta

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
LAT, LON, ALT = -24.6275, -70.4044, 2635.0
START, END = "2025-01-01", "2026-08-28"
HW = 2000.0   # GOWC water-vapour scale height (m)
H_MODEL = 2617.0  # Open-Meteo model-cell terrain height at Paranal (`elevation`)


def fetch_model_pwv():
    cache = os.path.join(HERE, "hfa_pwv_Paranal.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    r = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast",
                     params={"latitude": LAT, "longitude": LON,
                             "start_date": START, "end_date": END,
                             "hourly": "total_column_integrated_water_vapour",
                             "timezone": "UTC"}, timeout=180)
    r.raise_for_status()
    h = r.json()["hourly"]
    json.dump(h, open(cache, "w"))
    return h


def fetch_lhatpro():
    """Measured PWV (mm) per hour from the ESO ASM LHATPRO archive. Fetched in
    monthly chunks (the archive caps rows per query)."""
    cache = os.path.join(HERE, "lhatpro_paranal_2025_26.csv")
    if not os.path.exists(cache):
        base = "http://archive.eso.org/wdb/wdb/asm/lhatpro_paranal/query"
        rows = []
        y, m = 2025, 1
        while (y, m) <= (2026, 8):
            lo = f"{y}-{m:02d}-01"
            ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
            hi = f"{ny}-{nm:02d}-01"
            r = requests.get(base, params={
                "wdbo": "csv/download", "max_rows_returned": 500000,
                "tab_pwv0": "on", "start_date": f"{lo}..{hi}",
                "order": "start_date"}, timeout=120)
            for line in r.text.splitlines():
                if line and not line.startswith("#") and "Platform" not in line \
                        and not line.startswith("Date"):
                    rows.append(line)
            y, m = ny, nm
        open(cache, "w").write("\n".join(rows))
    # parse: PWV is the last populated numeric column
    bins = {}
    for line in open(cache):
        parts = line.split(",")
        if len(parts) < 6:
            continue
        try:
            t = datetime.fromisoformat(parts[1][:19]).replace(minute=0, second=0)
            pwv = float(parts[5])
        except (ValueError, IndexError):
            continue
        if pwv > 0:
            bins.setdefault(t, []).append(pwv)
    return {t: statistics.mean(v) for t, v in bins.items()}


def model_pwv_series(legacy=False):
    """Model PWV at the site. legacy=True reproduces the old sea-level scaling
    (the double-count bug) for comparison."""
    h = fetch_model_pwv()
    dz = ALT if legacy else max(0.0, ALT - H_MODEL)
    out = {}
    for i, ts in enumerate(h["time"]):
        col = h["total_column_integrated_water_vapour"][i]
        if col is None:
            continue
        pwv_site = col * math.exp(-dz / HW)   # GOWC's altitude correction
        out[datetime.fromisoformat(ts[:19])] = pwv_site
    return out


def nightly(hourly):
    byn = {}
    for t, v in hourly.items():
        n = (t - timedelta(hours=4)).date()
        byn.setdefault(n, []).append(v)
    return {d: statistics.median(vs) for d, vs in byn.items()}


def spearman(x, y):
    def rk(a):
        o = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a); i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[o[j + 1]] == a[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    return statistics.correlation(rk(x), rk(y))


def fisher_ci(rho, n):
    if n <= 3:
        return (float("nan"), float("nan"))
    zr = 0.5 * math.log((1 + rho) / (1 - rho)); se = 1 / math.sqrt(n - 3)
    return (math.tanh(zr - 1.96 * se), math.tanh(zr + 1.96 * se))


def main():
    model = nightly(model_pwv_series())
    meas = nightly(fetch_lhatpro())
    common = sorted(set(model) & set(meas))
    mv = [model[d] for d in common]
    dv = [meas[d] for d in common]
    rho = spearman(mv, dv)
    lo, hi = fisher_ci(rho, len(common))
    r_pearson = statistics.correlation(mv, dv)
    bias = statistics.median(mv[i] / dv[i] for i in range(len(mv)) if dv[i] > 0)
    med_ratio = statistics.median(mv) / statistics.median(dv)
    abserr = statistics.median(abs(mv[i] - dv[i]) for i in range(len(mv)))
    print(f"PWV: GOWC model column (x exp(-(h_site-h_model)/2000)) vs LHATPRO, Paranal")
    print(f"  nights N          = {len(common)}")
    print(f"  median GOWC PWV   = {statistics.median(mv):.2f} mm")
    print(f"  median LHATPRO    = {statistics.median(dv):.2f} mm")
    print(f"  Spearman rho      = {rho:+.3f}  [{lo:+.3f}, {hi:+.3f}]")
    print(f"  Pearson r         = {r_pearson:+.3f}")
    print(f"  ratio of medians  = {med_ratio:.2f}x  ({(med_ratio - 1) * 100:+.0f}% wet bias)")
    print(f"  median bias ratio = {bias:.2f}x  (per-night)")
    print(f"  median |error|    = {abserr:.2f} mm")

    legacy = nightly(model_pwv_series(legacy=True))
    lv = [legacy[d] for d in common if d in legacy]
    print(f"\n  Legacy sea-level scaling exp(-h_site/2000) (the double-count bug):")
    print(f"  median GOWC PWV   = {statistics.median(lv):.2f} mm  "
          f"({statistics.median(mv) / statistics.median(lv):.1f}x below corrected, "
          f"{statistics.median(dv) / statistics.median(lv):.1f}x below LHATPRO)")


if __name__ == "__main__":
    main()
