"""
Supplementary hindcast statistics for the GOWC paper (S4.5, Table 4 caption).

Reproduces the numbers hindcast_multiyear.py does not print:
  * per-calendar-year rho (2025 / 2026),
  * rho on nights OUTSIDE the calibration window (2026-05-29 .. 08-29),
  * rho under a stricter >=3-DIMM-hours-per-night filter,
  * partial Spearman of GOWC vs DIMM controlling for persistence (last night's DIMM),
  * marginal rho of the free-atmosphere and ground-layer terms separately, and the
    partial of the free-atmosphere term controlling for surface wind,
  * "will tonight be poor?" skill (DIMM > 1.0") at a rate-matched threshold,
  * dynamic-range compression (spread of log10 model vs log10 DIMM).

Uses the same cached Historical-Forecast-API profiles and ASM DIMM archives as
hindcast_multiyear.py. Partial Spearman = partial Pearson on ranks.

Run:  python tests/hindcast_extras.py
"""
import os
import sys
import math
import statistics
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import hindcast_multiyear as H   # noqa: E402
import atmospheric as a          # noqa: E402

CALIB_LO, CALIB_HI = date(2026, 5, 29), date(2026, 8, 29)
POOR = 1.0   # arcsec: a "poor" night


def _pearson(x, y):
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    return sxy / math.sqrt(sum((u - mx) ** 2 for u in x) * sum((v - my) ** 2 for v in y))


def spearman(x, y):
    return _pearson(H._ranks(x), H._ranks(y))


def partial_spearman(x, y, z):
    """Spearman correlation of x and y controlling for z."""
    rx, ry, rz = H._ranks(x), H._ranks(y), H._ranks(z)
    rxy, rxz, ryz = _pearson(rx, ry), _pearson(rx, rz), _pearson(ry, rz)
    return (rxy - rxz * ryz) / math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))


def components(site):
    """Hourly free-atmosphere seeing, ground-layer seeing and 10 m wind (m/s)."""
    h = H.fetch_profile(site)
    alt = H.SITES[site]["alt"]
    free, bl, wind = {}, {}, {}
    for i, ts in enumerate(h["time"]):
        def g(k):
            v = h.get(k, [])
            return v[i] if i < len(v) else None
        levels = [{"p": float(p), "t": g(f"temperature_{p}hPa"),
                   "z": g(f"geopotential_height_{p}hPa"),
                   "w": g(f"wind_speed_{p}hPa")} for p in (850, 700, 600, 500)]
        levels = [L for L in levels if L["t"] is not None and L["z"] is not None]
        t = datetime.fromisoformat(ts[:19])
        w = (g("wind_speed_10m") or 0) / 3.6          # km/h -> m/s, as the hindcast
        f = a.free_atmosphere_seeing_multilevel(levels, alt, airmass=1.0)
        if f is not None:
            free[t] = f
        bl[t] = a._boundary_layer_seeing(w, None, alt, 1.0)
        wind[t] = w
    return free, bl, wind


def night_counts(hourly):
    """Number of hourly bins per observing night (same night key as the hindcast)."""
    counts = {}
    for t in hourly:
        d = next(iter(H.nightly_medians({t: 0.0})))
        counts[d] = counts.get(d, 0) + 1
    return counts


def analyse(site):
    print(f"\n{'=' * 60}\n{site}\n{'=' * 60}")
    pn = H.nightly_medians(H.gowc_hourly(site))
    dimm = H.measured_hourly(H.SITES[site]["dimm"], "seeing")
    dn = H.nightly_medians(dimm)
    cn = sorted(set(pn) & set(dn))

    def rho(days):
        return spearman([pn[d] for d in days], [dn[d] for d in days])

    print(f"  all nights            N={len(cn)}  rho={rho(cn):+.3f}")
    for yr in (2025, 2026):
        c = [d for d in cn if d.year == yr]
        print(f"  {yr}                  N={len(c)}  rho={rho(c):+.3f}")
    out = [d for d in cn if not (CALIB_LO <= d <= CALIB_HI)]
    print(f"  outside calib window  N={len(out)}  rho={rho(out):+.3f}")
    counts = night_counts(dimm)
    c3 = [d for d in cn if counts.get(d, 0) >= 3]
    print(f"  >=3 DIMM bins/night   N={len(c3)}  rho={rho(c3):+.3f}")

    trip = [(pn[cn[i]], dn[cn[i]], dn[cn[i - 1]]) for i in range(1, len(cn))
            if (cn[i] - cn[i - 1]).days == 1]
    x, y, z = zip(*trip)
    print(f"\n  persistence rho       = {spearman(z, y):+.3f}  (N={len(trip)})")
    print(f"  partial(GOWC, DIMM | persistence) = {partial_spearman(x, y, z):+.3f}")

    free, bl, wind = components(site)
    fn, bn, wn = (H.nightly_medians(s) for s in (free, bl, wind))
    c = [d for d in cn if d in fn and d in wn]
    fv, bv, wv, dv = ([s[d] for d in c] for s in (fn, bn, wn, dn))
    print(f"\n  free-atmosphere term rho = {spearman(fv, dv):+.3f}  (N={len(c)})")
    print(f"  ground-layer term rho    = {spearman(bv, dv):+.3f}")
    print(f"  partial(free, DIMM | surface wind) = {partial_spearman(fv, dv, wv):+.3f}")

    xs = [pn[d] for d in cn]
    poor = [dn[d] > POOR for d in cn]
    base = sum(poor) / len(poor)
    thr = sorted(xs)[int(round((1 - base) * len(xs)))]   # rate-matched threshold
    flag = [v >= thr for v in xs]
    tp = sum(f and p for f, p in zip(flag, poor))
    fp = sum(f and not p for f, p in zip(flag, poor))
    print(f"\n  poor nights (DIMM > {POOR}\"): base rate {base:.1%}")
    print(f"  recall {tp / sum(poor):.1%}  false-alarm {fp / (len(poor) - sum(poor)):.1%}  "
          f"precision {tp / sum(flag):.1%}")

    sm = statistics.pstdev([math.log10(v) for v in xs])
    sd = statistics.pstdev([math.log10(dn[d]) for d in cn])
    print(f"\n  spread log10: model {sm:.3f} dex, DIMM {sd:.3f} dex, ratio {sm / sd:.2f}")


if __name__ == "__main__":
    for s in H.SITES:
        analyse(s)
