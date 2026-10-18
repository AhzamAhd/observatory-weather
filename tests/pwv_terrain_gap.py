"""
How often GOWC's PWV altitude correction actually applies (paper S3.3).

GOWC removes water between Open-Meteo's `elevation` (a 90 m digital-elevation-
model height at the site's coordinates) and the site altitude:
PWV(site) = PWV_OM exp(-(h_site - h_DEM)/2000 m), only when h_site > h_DEM.
Because site altitudes come from the same elevation service, the gap is zero for
almost every catalogued site.

Uses the snapshot tests/site_terrain_snapshot.csv (site altitude and the
`elevation` stored with each site's latest weather reading). If the snapshot is
missing, it is rebuilt from the GOWC database (needs the Supabase credentials).

Run:  python tests/pwv_terrain_gap.py
"""
import csv
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "site_terrain_snapshot.csv")
HW = 2000.0


def load():
    if not os.path.exists(SNAPSHOT):
        sys.path.insert(0, os.path.dirname(HERE))
        import db
        d = db.query_df("""
            SELECT DISTINCT ON (o.id) o.id, o.mpc_code, o.altitude_m,
                   w.model_elevation_m AS dem_elevation_m
            FROM weather_readings w JOIN observatories o ON o.id = w.observatory_id
            WHERE w.model_elevation_m IS NOT NULL
            ORDER BY o.id, w.fetch_datetime DESC""")
        d.to_csv(SNAPSHOT, index=False)
    with open(SNAPSHOT, newline="") as f:
        return [(float(r["altitude_m"]), float(r["dem_elevation_m"]))
                for r in csv.DictReader(f)]


def main():
    rows = load()
    gaps = [max(0.0, h - dem) for h, dem in rows]
    n = len(gaps)
    zero = sum(g == 0 for g in gaps)
    print(f"sites with a stored elevation : {n}")
    print(f"correction exactly zero       : {zero} ({100 * zero / n:.1f}%)")
    print(f"gap > 200 m                   : {sum(g > 200 for g in gaps)}")
    print(f"gap > 500 m                   : {sum(g > 500 for g in gaps)}")
    fac = [math.exp(-g / HW) for g in gaps]
    print(f"correction factor: median {statistics.median(fac):.3f}, min {min(fac):.3f}")


if __name__ == "__main__":
    main()
