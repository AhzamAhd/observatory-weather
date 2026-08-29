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
                   w.temp_850hpa, w.temp_500hpa, w.geopot_850hpa,
                   w.geopot_500hpa, w.wind_850hpa, w.jet_stream_ms
            FROM weather_readings w JOIN observatories o ON o.id = w.observatory_id
            WHERE o.name ILIKE '{pat}'
              AND w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
            ORDER BY o.altitude_m DESC LIMIT 1
        """)
        if r.empty:
            continue
        rec = dict(r.iloc[0])
        rec["altitude_m"] = rec.get("altitude_m") or 0
        seeing = get_full_atmospheric_analysis(rec).get("seeing_arcsec")
        if seeing is not None:
            rows.append((now, label, seeing))

    new_file = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        wr = csv.writer(f)
        if new_file:
            wr.writerow(["datetime_utc", "site", "gowc_seeing"])
        wr.writerows(rows)
    print(f"Logged {len(rows)} site(s) at {now}")
    for _, label, s in rows:
        print(f"  {label:14} GOWC seeing = {s}\"")


def _read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def compare_to_dimm():
    """Match logged GOWC forecasts to measured DIMM values and report stats."""
    gowc = _read_csv(LOG_PATH)
    dimm = _read_csv(DIMM_PATH)
    if not gowc:
        print("No GOWC log yet. Run 'log' daily first.")
        return
    if not dimm:
        print(f"No DIMM data. Download it and save to {DIMM_PATH} "
              "(columns: datetime_utc, site, dimm_seeing).")
        return

    # Match by (site, date) --- forecasts and DIMM rarely share the exact minute.
    def key(row):
        return (row["site"].strip().lower(), row["datetime_utc"][:10])

    dimm_map = {}
    for d in dimm:
        dimm_map.setdefault(key(d), []).append(float(d["dimm_seeing"]))

    pairs = []
    for g in gowc:
        k = key(g)
        if k in dimm_map:
            measured = sum(dimm_map[k]) / len(dimm_map[k])  # daily mean DIMM
            pairs.append((g["site"], float(g["gowc_seeing"]), measured))

    if not pairs:
        print("No matched (site, date) pairs yet --- keep logging / add DIMM data.")
        return

    import statistics
    gv = [p[1] for p in pairs]
    dv = [p[2] for p in pairs]
    n = len(pairs)
    bias = statistics.mean(gv[i] - dv[i] for i in range(n))
    rms = (sum((gv[i] - dv[i]) ** 2 for i in range(n)) / n) ** 0.5
    ratio = statistics.median(gv[i] / dv[i] for i in range(n) if dv[i] > 0)
    try:
        corr = statistics.correlation(gv, dv) if n >= 2 else float("nan")
    except Exception:
        corr = float("nan")

    print(f"\n  GOWC vs measured DIMM seeing  (N = {n} matched pairs)")
    print("  " + "-" * 44)
    print(f"  correlation r : {corr:.2f}")
    print(f"  median ratio  : {ratio:.2f}  (GOWC / DIMM)")
    print(f"  bias          : {bias:+.2f}\"  (GOWC - DIMM)")
    print(f"  RMS           : {rms:.2f}\"")
    print("  " + "-" * 44)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        lim = max(max(gv), max(dv)) * 1.1
        plt.figure(figsize=(5, 5))
        plt.scatter(dv, gv, s=18, alpha=0.7)
        plt.plot([0, lim], [0, lim], "k--", lw=1, label="1:1")
        plt.xlabel("Measured DIMM seeing (arcsec)")
        plt.ylabel("GOWC forecast seeing (arcsec)")
        plt.title(f"GOWC vs DIMM  (N={n}, r={corr:.2f})")
        plt.xlim(0, lim); plt.ylim(0, lim)
        plt.legend(); plt.tight_layout()
        plt.savefig(PLOT_PATH, dpi=130)
        print(f"  Plot -> {PLOT_PATH}")
    except ImportError:
        print("  (install matplotlib for a scatter plot)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "log"
    if cmd == "log":
        log_seeing()
    elif cmd == "compare":
        compare_to_dimm()
    else:
        print("Usage: python tests/dimm_seeing_log.py [log|compare]")
