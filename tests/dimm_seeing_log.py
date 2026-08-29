"""
Forward seeing log for DIMM validation.

GOWC's Tatarski seeing needs upper-air (850/500 hPa) data, which the free
weather archive does not serve for past dates --- so a historical reconstruction
is not possible. Instead we log GOWC's LIVE seeing forecast each day for the
DIMM-equipped sites, building matched pairs against measured DIMM seeing over
time. After a few weeks of logging, compare_to_dimm() produces the validation.

USAGE
-----
1. Log GOWC's seeing (run daily, e.g. from cron / GitHub Actions):
       python tests/dimm_seeing_log.py log

2. Download DIMM seeing from the observatory archive for the same dates, e.g.
   ESO Paranal MASS-DIMM:
       http://archive.eso.org/cms/eso-data/ambient-conditions/paranal-ambient-query-forms.html
   Save it as tests/dimm_measured.csv with columns:  datetime_utc, site, dimm_seeing

3. Compare:
       python tests/dimm_seeing_log.py compare

The comparison reports N, correlation, bias and RMS, and (if matplotlib is
present) writes a scatter plot to tests/dimm_validation.png.
"""
import sys
import os
import csv
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import query_df                              # noqa: E402
from atmospheric import get_full_atmospheric_analysis  # noqa: E402

LOG_PATH = os.path.join(os.path.dirname(__file__), "gowc_seeing_log.csv")
DIMM_PATH = os.path.join(os.path.dirname(__file__), "dimm_measured.csv")
PWV_PATH = os.path.join(os.path.dirname(__file__), "pwv_measured.csv")
PLOT_PATH = os.path.join(os.path.dirname(__file__), "dimm_validation.png")

# DIMM-equipped sites with public archives (name pattern -> short label).
SITES = {
    "%Paranal%":       "Paranal",
    "%La Silla%":      "La Silla",
    "%Cerro Tololo%":  "Cerro Tololo",
    "%La Palma-TNG%":  "La Palma",
}


def log_seeing():
    """Append the current GOWC seeing forecast for each DIMM site to the log."""
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = []
    for pat, label in SITES.items():
        r = query_df(f"""
            SELECT o.name, o.altitude_m, o.latitude, w.temperature_c,
                   w.humidity_pct, w.wind_speed_ms, w.surface_pressure,
                   w.temp_850hpa, w.temp_700hpa, w.temp_600hpa, w.temp_500hpa,
                   w.geopot_850hpa, w.geopot_700hpa, w.geopot_600hpa,
                   w.geopot_500hpa, w.wind_850hpa, w.wind_700hpa, w.wind_600hpa,
                   w.wind_500hpa, w.jet_stream_ms
            FROM weather_readings w JOIN observatories o ON o.id = w.observatory_id
            WHERE o.name ILIKE '{pat}'
              AND w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
            ORDER BY o.altitude_m DESC LIMIT 1
        """)
        if r.empty:
            continue
        rec = dict(r.iloc[0])
        rec["altitude_m"] = rec.get("altitude_m") or 0
        a = get_full_atmospheric_analysis(rec)
        seeing = a.get("seeing_arcsec")
        pwv = a.get("pwv_mm")
        if seeing is not None:
            rows.append((now, label, seeing, pwv))

    new_file = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        wr = csv.writer(f)
        if new_file:
            wr.writerow(["datetime_utc", "site", "gowc_seeing", "gowc_pwv"])
        wr.writerows(rows)
    print(f"Logged {len(rows)} site(s) at {now}")
    for _, label, s, p in rows:
        print(f"  {label:14} GOWC seeing = {s}\"  PWV = {p} mm")


def _read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _find_col(fieldnames, *candidates):
    """Find the first column whose name contains any candidate (case-insensitive)."""
    low = {c.lower(): c for c in fieldnames}
    for cand in candidates:
        for lc, orig in low.items():
            if cand in lc:
                return orig
    return None


def _load_measured(path, value_kinds):
    """Load an observatory-archive CSV. Auto-detects the timestamp column and the
    value column (seeing or PWV) by name. Returns list of (date10, value)."""
    if not os.path.exists(path):
        return None
    rows = _read_csv(path)
    if not rows:
        return []
    fn = rows[0].keys()
    tcol = _find_col(fn, "date", "time", "mjd", "night")
    vcol = _find_col(fn, *value_kinds)
    if not tcol or not vcol:
        print(f"  Could not auto-detect columns in {os.path.basename(path)}.")
        print(f"  Columns found: {list(fn)}")
        return []
    out = []
    for r in rows:
        try:
            val = float(r[vcol])
        except (ValueError, TypeError, KeyError):
            continue
        out.append((str(r[tcol])[:10], val))
    return out


def _stats(gv, dv):
    import statistics
    n = len(gv)
    bias = statistics.mean(gv[i] - dv[i] for i in range(n))
    rms = (sum((gv[i] - dv[i]) ** 2 for i in range(n)) / n) ** 0.5
    ratio = statistics.median(gv[i] / dv[i] for i in range(n) if dv[i] > 0)
    try:
        corr = statistics.correlation(gv, dv) if n >= 2 else float("nan")
    except Exception:
        corr = float("nan")
    return n, corr, ratio, bias, rms


def compare(quantity="seeing", site="Paranal", measured_file=None):
    """Compare GOWC forecasts to measured archive data for one site.

    quantity : 'seeing' or 'pwv'
    site     : which logged site to compare (e.g. 'Paranal', 'La Silla')
    measured_file : path to the downloaded archive CSV (defaults per quantity)

    Reports a distribution comparison (works immediately on a large historical
    download) and, where dates overlap, matched-pair stats + a scatter plot."""
    gowc_rows = _read_csv(LOG_PATH)
    if not gowc_rows:
        print("No GOWC log yet. Run 'log' first (it runs automatically in CI).")
        return

    if quantity == "pwv":
        gcol, default_path = "gowc_pwv", PWV_PATH
        vkinds, unit, label = ("pwv", "water vapour", "precip"), "mm", "PWV"
    else:
        gcol, default_path = "gowc_seeing", DIMM_PATH
        vkinds, unit, label = ("seeing", "fwhm"), "\"", "seeing"
    measured_path = measured_file or default_path

    measured = _load_measured(measured_path, vkinds)
    if measured is None:
        print(f"No measured file at {measured_path}. Download the archive data "
              "there (or pass its path as the 3rd argument).")
        return
    if not measured:
        return

    print(f"  Site: {site}   |   quantity: {label}   |   "
          f"measured file: {os.path.basename(measured_path)}")

    # GOWC values by date for THIS site only (daily mean across log entries)
    gowc_by_date = {}
    for g in gowc_rows:
        if g.get("site", "").strip().lower() != site.strip().lower():
            continue
        v = g.get(gcol)
        if v in (None, "", "None"):
            continue
        gowc_by_date.setdefault(g["datetime_utc"][:10], []).append(float(v))
    measured_by_date = {}
    for d10, val in measured:
        measured_by_date.setdefault(d10, []).append(val)

    gvals = [v for vs in gowc_by_date.values() for v in vs]
    mvals = [v for vs in measured_by_date.values() for v in vs]

    # 1) Distribution comparison (always available)
    import statistics
    print(f"\n  GOWC vs measured {label} --- DISTRIBUTION")
    print("  " + "-" * 46)
    print(f"  GOWC     : median {statistics.median(gvals):.2f}{unit}  "
          f"mean {statistics.mean(gvals):.2f}  (N={len(gvals)})")
    print(f"  measured : median {statistics.median(mvals):.2f}{unit}  "
          f"mean {statistics.mean(mvals):.2f}  (N={len(mvals)})")
    print(f"  median ratio (GOWC/measured): "
          f"{statistics.median(gvals)/statistics.median(mvals):.2f}")

    # 2) Matched-pair comparison (needs overlapping dates)
    pairs_g, pairs_m = [], []
    for d10, gv in gowc_by_date.items():
        if d10 in measured_by_date:
            pairs_g.append(sum(gv) / len(gv))
            pairs_m.append(sum(measured_by_date[d10]) / len(measured_by_date[d10]))
    if pairs_g:
        n, corr, ratio, bias, rms = _stats(pairs_g, pairs_m)
        print(f"\n  GOWC vs measured {label} --- MATCHED PAIRS  (N={n})")
        print("  " + "-" * 46)
        print(f"  correlation r : {corr:.2f}")
        print(f"  median ratio  : {ratio:.2f}")
        print(f"  bias          : {bias:+.2f}{unit}")
        print(f"  RMS           : {rms:.2f}{unit}")
        _plot(pairs_m, pairs_g, label, unit, corr, quantity)
    else:
        print("\n  (No matched dates yet --- the forward log needs to overlap the "
              "measured range. Distribution comparison above is usable now.)")


def _plot(mv, gv, label, unit, corr, quantity):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        lim = max(max(gv), max(mv)) * 1.1
        plt.figure(figsize=(5, 5))
        plt.scatter(mv, gv, s=18, alpha=0.7)
        plt.plot([0, lim], [0, lim], "k--", lw=1, label="1:1")
        plt.xlabel(f"Measured {label} ({unit})")
        plt.ylabel(f"GOWC forecast {label} ({unit})")
        plt.title(f"GOWC vs measured {label}  (N={len(gv)}, r={corr:.2f})")
        plt.xlim(0, lim); plt.ylim(0, lim)
        plt.legend(); plt.tight_layout()
        out = PLOT_PATH.replace("validation", f"validation_{quantity}")
        plt.savefig(out, dpi=130)
        print(f"  Plot -> {out}")
    except ImportError:
        print("  (install matplotlib for a scatter plot)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "log"
    if cmd == "log":
        log_seeing()
    elif cmd == "compare":
        quantity = sys.argv[2] if len(sys.argv) > 2 else "seeing"
        site = sys.argv[3] if len(sys.argv) > 3 else "Paranal"
        mfile = sys.argv[4] if len(sys.argv) > 4 else None
        compare(quantity, site, mfile)
    else:
        print("Usage: python tests/dimm_seeing_log.py log")
        print("       python tests/dimm_seeing_log.py compare "
              "[seeing|pwv] [site] [measured_file.csv]")
