"""
Absolute-bias sanity check (paper Table 3): GOWC's median seeing at sites with a
published DIMM median but no ASM archive in this work.

GOWC is evaluated with the live model (calculate_seeing_tatarski, per-level,
winds in m/s) on Open-Meteo Historical-Forecast fields over the same baseline as
the DIMM hindcast, using night hours only (local solar time 20:00-06:00), and
reduced to the median of nightly medians -- the same statistic as the hindcast
sites. Paranal and La Silla come from tests/hindcast_multiyear.py.

Run:  python tests/site_bias.py
"""
import json
import os
import statistics
import sys
from datetime import datetime, timedelta

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import hindcast_multiyear as H   # noqa: E402

SITES = {
    # name: (lat, lon, alt_m, published median, reference)
    "La Palma (ORM)": (28.7606, -17.8816, 2360.0, 0.76,
                       "Munoz-Tunon et al. 1997 (DIMM mean)"),
    "Mauna Kea (13N)": (19.8329, -155.4810, 4050.0, 0.75,
                        "Schoeck et al. 2009 (TMT 13N DIMM median)"),
}


def profile(name, lat, lon):
    cache = os.path.join(HERE, f"hfa_{name.split()[0].replace(' ', '')}{name.split()[1].strip('()')}.json")
    if os.path.exists(cache):
        h = json.load(open(cache))
    else:
        r = requests.get(H.HFA, params={
            "latitude": lat, "longitude": lon, "start_date": H.START,
            "end_date": H.END, "hourly": ",".join(H.PVARS), "timezone": "UTC"},
            timeout=300)
        r.raise_for_status()
        h = r.json()["hourly"]
        json.dump(h, open(cache, "w"))
    return {k: ([None if v is None else v / H.KMH_PER_MS for v in vals]
                if k.startswith("wind_speed_") else vals) for k, vals in h.items()}


def night_median(name, lat, lon, alt):
    h = profile(name, lat, lon)
    by_night = {}
    for i, ts in enumerate(h["time"]):
        t = datetime.fromisoformat(ts[:19])
        local = t + timedelta(hours=lon / 15.0)          # local solar time
        if not (local.hour >= 20 or local.hour < 6):
            continue
        g = lambda k: (h.get(k, [])[i] if i < len(h.get(k, [])) else None)
        t8, t5 = g("temperature_850hPa"), g("temperature_500hPa")
        z8, z5 = g("geopotential_height_850hPa"), g("geopotential_height_500hPa")
        if None in (t8, t5, z8, z5):
            continue
        s = H.a.calculate_seeing_tatarski(
            t8, t5, z8, z5, wind_850_ms=g("wind_speed_850hPa"),
            wind_500_ms=g("wind_speed_500hPa"), wind_250_ms=g("wind_speed_250hPa"),
            airmass=1.0, surface_wind_ms=g("wind_speed_10m"), altitude_m=alt,
            levels=H._levels(g))
        if s is not None:
            by_night.setdefault((local - timedelta(hours=12)).date(), []).append(s)
    return statistics.median(statistics.median(v) for v in by_night.values()), len(by_night)


def main():
    rows = []
    for site in ("Paranal", "La Silla"):
        dimm = H.measured_hourly(H.SITES[site]["dimm"], "seeing")
        pn = H.nightly_medians(H.gowc_hourly(site), hours=dimm)
        dn = H.nightly_medians(dimm)
        c = sorted(set(pn) & set(dn))
        rows.append((site, statistics.median(pn[d] for d in c),
                     statistics.median(dn[d] for d in c), "ASM DIMM, this work", len(c)))
    for name, (lat, lon, alt, meas, ref) in SITES.items():
        g, n = night_median(name, lat, lon, alt)
        rows.append((name, g, meas, ref, n))

    print(f"\n  {'site':18} {'GOWC':>6} {'meas':>6} {'bias':>6}  nights  reference")
    held = []
    for site, g, m, ref, n in rows:
        print(f"  {site:18} {g:6.2f} {m:6.2f} {(g / m - 1) * 100:+5.0f}%  {n:6d}  {ref}")
        if site != "Paranal":
            held.append((g, m))
    mae_model = statistics.fmean(abs(g / m - 1) for g, m in held)
    const = rows[0][2]                         # Paranal's measured median
    mae_const = statistics.fmean(abs(const / m - 1) for _, m in held)
    print(f"\n  held-out sites: model MAE {mae_model:.1%}; "
          f"constant {const:.3f}\" (Paranal's measured median) predictor "
          f"MAE {mae_const:.1%}")


if __name__ == "__main__":
    main()
