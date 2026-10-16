"""
Supplementary hindcast statistics for the GOWC paper (S4.6, Table 4).

Uses the conventions of hindcast_multiyear.py (winds in m/s, noon-to-noon
nights, model sampled only at the hours DIMM measured). Reproduces:
  * per-calendar-year rho and rho outside the calibration window,
  * rho under a stricter >=3-DIMM-hours-per-night filter,
  * partial Spearman of GOWC vs DIMM controlling for persistence and for
    surface wind,
  * marginal rho of the free-atmosphere and ground-layer terms separately, and
    the partial of the free-atmosphere term controlling for surface wind,
  * "will tonight be poor?" skill (DIMM > 1.0") at a rate-matched threshold,
  * dynamic-range compression and the debiased log scatter.

Partial Spearman = partial Pearson on ranks.

Run:  python tests/hindcast_extras.py
"""
import os
import sys
import math
import statistics
from datetime import date

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


def ground_hourly(site):
    alt = H.SITES[site]["alt"]
    return {t: a._boundary_layer_seeing(w, None, alt, 1.0)
            for t, w in H.surface_wind_hourly(site).items()}


def analyse(site):
    print(f"\n{'=' * 60}\n{site}\n{'=' * 60}")
    dimm = H.measured_hourly(H.SITES[site]["dimm"], "seeing")
    pn = H.nightly_medians(H.gowc_hourly(site), hours=dimm)
    dn = H.nightly_medians(dimm)
    cn = sorted(set(pn) & set(dn))

    def rho(days):
        return spearman([pn[d] for d in days], [dn[d] for d in days])

    print(f"  all nights            N={len(cn)}  rho={rho(cn):+.3f}")
    for yr in (2025, 2026):
        c = [d for d in cn if d.year == yr]
        print(f"  {yr}                  N={len(c)}  rho={rho(c):+.3f}")
    stray = [d for d in cn if d.year < 2025]
    if stray:
        print(f"  (+{len(stray)} night keyed {stray[0]}: the first UTC hours of 2025-01-01)")
    out = [d for d in cn if not (CALIB_LO <= d <= CALIB_HI)]
    print(f"  outside calib window  N={len(out)}  rho={rho(out):+.3f}  "
          f"CI[{H.fisher_ci(rho(out), len(out))[0]:+.2f},{H.fisher_ci(rho(out), len(out))[1]:+.2f}]")
    counts = {}
    for t in dimm:
        counts[H.night_of(t)] = counts.get(H.night_of(t), 0) + 1
    c3 = [d for d in cn if counts.get(d, 0) >= 3]
    print(f"  >=3 DIMM hours/night  N={len(c3)}  rho={rho(c3):+.3f}")

    trip = [(pn[cn[i]], dn[cn[i]], dn[cn[i - 1]]) for i in range(1, len(cn))
            if (cn[i] - cn[i - 1]).days == 1]
    x, y, z = zip(*trip)
    print(f"\n  persistence rho       = {spearman(z, y):+.3f}  (N={len(trip)})")
    print(f"  partial(GOWC, DIMM | persistence) = {partial_spearman(x, y, z):+.3f}")

    fn = H.nightly_medians(H.free_hourly(site), hours=dimm)
    gn = H.nightly_medians(ground_hourly(site), hours=dimm)
    wn = H.nightly_medians(H.surface_wind_hourly(site), hours=dimm)
    c = [d for d in cn if d in fn and d in wn and d in gn]
    fv, gv, wv, dv, pv = ([s[d] for d in c] for s in (fn, gn, wn, dn, pn))
    print(f"\n  free-atmosphere term rho = {spearman(fv, dv):+.3f}  (N={len(c)})")
    print(f"  ground-layer term rho    = {spearman(gv, dv):+.3f}")
    print(f"  surface wind rho         = {spearman(wv, dv):+.3f}")
    print(f"  partial(free, DIMM | surface wind) = {partial_spearman(fv, dv, wv):+.3f}")
    print(f"  partial(GOWC, DIMM | surface wind) = {partial_spearman(pv, dv, wv):+.3f}")

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

    lm = [math.log10(v) for v in xs]
    ld = [math.log10(dn[d]) for d in cn]
    sm, sd = statistics.pstdev(lm), statistics.pstdev(ld)
    mx, my = statistics.fmean(ld), statistics.fmean(lm)
    slope = (sum((u - mx) * (v - my) for u, v in zip(ld, lm))
             / sum((u - mx) ** 2 for u in ld))
    off = statistics.median(v - u for u, v in zip(ld, lm))
    rms = math.sqrt(statistics.fmean((v - u - off) ** 2 for u, v in zip(ld, lm)))
    print(f"\n  spread log10: model {sm:.3f} dex, DIMM {sd:.3f} dex, ratio {sm / sd:.2f};"
          f" OLS slope {slope:.2f}; debiased RMS {rms:.2f} dex")


if __name__ == "__main__":
    for s in H.SITES:
        analyse(s)
