"""
One-off repair of the `observatories` table (Oct 2026).

The original MPC import (build_observatory_list.py, since fixed) had three bugs:
  1. Fixed-column slicing pushed a digit of rho*sin(phi') into the name
     ("8  Armagh") -- ~1,100 names.
  2. Latitude was the GEOCENTRIC atan2(rho sin, rho cos), not the geodetic one:
     ~0.19 deg (~21 km) too close to the equator, so elevations looked up at
     those coordinates are wrong too (e.g. La Palma at 548 m, not ~2,330 m).
  3. Countries came from overlapping rough boxes (Peru -> "Brazil", northern
     Chile -> "Argentina") and ~54% were "Unknown".

For each row whose name/latitude still match the buggy MPC derivation, this sets
the clean MPC name, the geodetic latitude and a fresh DEM elevation (Open-Meteo
elevation API). Hand-added or hand-edited rows keep their name and coordinates.
Every row gets a country from Natural Earth borders (geo_country.py). Names in
`subscriptions` and `observatory_reviews` are renamed in the same transaction.

Before writing, the current `observatories`, `subscriptions` and
`observatory_reviews` rows are saved to backups/ so the change can be reverted.

Run:  python fix_observatory_metadata.py            (dry run: report only)
      python fix_observatory_metadata.py --apply    (backup, then one transaction)
"""
import csv
import math
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

from build_observatory_list import _MPC_LINE, parallax_to_geodetic
from db import _run, query_df
from geo_country import country_for

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

MPC_URL = "https://www.minorplanetcenter.net/iau/lists/ObsCodesF.html"
PREFIX = re.compile(r"^\d\s+")
REPORT = "observatory_metadata_changes.csv"


def mpc_entries():
    """{code: (clean name, geodetic lat, buggy geocentric lat)} from the live list."""
    from bs4 import BeautifulSoup
    r = requests.get(MPC_URL, timeout=60)
    r.raise_for_status()
    pre = BeautifulSoup(r.text, "html.parser").find("pre")
    out = {}
    for line in pre.text.split("\n"):
        m = _MPC_LINE.match(line)
        if not m:
            continue
        code, _lon, cos_s, sin_s, name = m.groups()
        try:
            lat, _ = parallax_to_geodetic(float(cos_s), float(sin_s))
            # Reproduce the OLD derivation (fixed columns, geocentric) to recognise
            # rows that still carry it.
            geoc = math.degrees(math.atan2(float(line[21:30]), float(line[13:21])))
        except ValueError:
            continue
        out[code] = (name, lat, geoc)
    return out


def elevations(coords):
    """DEM elevation (m) for [(lat, lon)], batched 100 per Open-Meteo call."""
    out = []
    for i in range(0, len(coords), 100):
        chunk = coords[i:i + 100]
        for attempt in range(6):
            r = requests.get("https://api.open-meteo.com/v1/elevation", params={
                "latitude": ",".join(f"{la:.4f}" for la, _ in chunk),
                "longitude": ",".join(f"{lo:.4f}" for _, lo in chunk)}, timeout=60)
            if r.status_code != 429 and r.status_code < 500:
                break
            time.sleep(10 * (attempt + 1))      # rate limit / transient outage
        r.raise_for_status()
        out.extend(r.json()["elevation"])
        time.sleep(1)
    return out


def plan():
    obs = query_df("SELECT id, name, mpc_code, latitude, longitude, altitude_m, "
                   "country FROM observatories ORDER BY id")
    mpc = mpc_entries()
    changes, relocate = [], []
    for _, o in obs.iterrows():
        name, lat, lon = o["name"], float(o["latitude"]), float(o["longitude"])
        stripped = PREFIX.sub("", name)
        m = mpc.get(o["mpc_code"])
        if m and stripped == m[0] and abs(lat - m[2]) < 0.002:
            kind, name, lat = "mpc-derived", m[0], round(m[1], 4)
        elif stripped != name:
            kind, name = "prefix-only", stripped
        else:
            kind = "hand-curated"
        if kind == "mpc-derived" and abs(lat - float(o["latitude"])) > 1e-6:
            relocate.append(len(changes))
        alt = None if o["altitude_m"] is None else int(o["altitude_m"])
        changes.append({
            "id": int(o["id"]), "mpc_code": o["mpc_code"], "kind": kind,
            "old_name": o["name"], "new_name": name,
            "old_lat": float(o["latitude"]), "new_lat": lat, "lon": lon,
            "old_alt": alt, "new_alt": alt,
            "old_country": o["country"], "new_country": country_for(lat, lon),
        })

    # `name` is UNIQUE. A few distinct MPC stations share a name (e.g. two
    # "Tosa"); suffix the renamed row with its code, leaving the other untouched.
    counts = {}
    for c in changes:
        counts[c["new_name"]] = counts.get(c["new_name"], 0) + 1
    for c in changes:
        if counts[c["new_name"]] > 1 and c["new_name"] != c["old_name"]:
            c["new_name"] = f"{c['new_name']} (MPC {c['mpc_code']})"
    assert len({c["new_name"] for c in changes}) == len(changes), "name collision"

    print(f"  Looking up DEM elevation for {len(relocate)} relocated sites...")
    elev = elevations([(changes[i]["new_lat"], changes[i]["lon"]) for i in relocate])
    for i, e in zip(relocate, elev):
        if e is not None and not math.isnan(e):
            changes[i]["new_alt"] = int(round(max(0.0, e)))
    return changes


def report(changes):
    with open(REPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(changes[0].keys()))
        w.writeheader()
        w.writerows(changes)
    kinds = {}
    for c in changes:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    renamed = sum(c["old_name"] != c["new_name"] for c in changes)
    moved = [c for c in changes if abs(c["old_lat"] - c["new_lat"]) > 1e-6]
    dalt = [c for c in changes if c["old_alt"] is not None and c["new_alt"] is not None
            and abs(c["new_alt"] - c["old_alt"]) >= 300]
    recountry = sum(c["old_country"] != c["new_country"] for c in changes)
    unknown = sum(c["new_country"] == "Unknown" for c in changes)
    print(f"\n  rows: {len(changes)}  {kinds}")
    print(f"  renamed: {renamed}   latitude corrected: {len(moved)} (max shift "
          f"{max((abs(c['old_lat'] - c['new_lat']) for c in moved), default=0):.3f} deg)")
    print(f"  altitude change >= 300 m: {len(dalt)}")
    print(f"  country changed: {recountry}   still Unknown: {unknown}")
    print("\n  Largest altitude corrections:")
    for c in sorted(dalt, key=lambda c: -abs(c["new_alt"] - c["old_alt"]))[:12]:
        print(f"    {c['new_name'][:42]:<42} {c['old_alt']:>5} -> {c['new_alt']:>5} m")
    print(f"\n  Full report: {os.path.abspath(REPORT)}")


def backup():
    os.makedirs("backups", exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for table in ("observatories", "subscriptions", "observatory_reviews"):
        df = query_df(f"SELECT * FROM {table}")
        path = os.path.join("backups", f"{table}_{stamp}.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"  Backed up {len(df)} rows -> {path}")


def apply(changes):
    renames = [(c["old_name"], c["new_name"]) for c in changes
               if c["old_name"] != c["new_name"]]

    from psycopg2.extras import execute_values
    from psycopg2.errors import LockNotAvailable

    rows = [(c["id"], c["new_name"], c["new_lat"], c["new_alt"], c["new_country"])
            for c in changes]

    def work(conn):
        cur = conn.cursor()
        # Concurrent weather upserts take KEY SHARE locks on the rows they
        # reference, which a rename of the UNIQUE `name` column must wait for.
        # Fail fast on a lock instead of hanging into statement_timeout.
        cur.execute("SET LOCAL lock_timeout = '15s'")
        cur.execute("SET LOCAL statement_timeout = '5min'")
        # Two phases so a swap of names between rows can never trip UNIQUE(name)
        # mid-statement: park every renamed row on a unique temporary name first.
        cur.execute("UPDATE observatories SET name = '__tmp_' || id || '_' || name "
                    "WHERE id = ANY(%s)",
                    ([c["id"] for c in changes if c["old_name"] != c["new_name"]],))
        execute_values(cur, """
            UPDATE observatories AS o
            SET name = v.name, latitude = v.lat, altitude_m = v.alt, country = v.country
            FROM (VALUES %s) AS v(id, name, lat, alt, country)
            WHERE o.id = v.id""", rows,
            template="(%s::int, %s::text, %s::float8, %s::int, %s::text)",
            page_size=len(rows))
        if renames:
            for table in ("subscriptions", "observatory_reviews"):
                execute_values(cur, f"""
                    UPDATE {table} AS t SET observatory = v.new
                    FROM (VALUES %s) AS v(old, new)
                    WHERE t.observatory = v.old""", renames, page_size=len(renames))
        conn.commit()
        cur.close()

    for attempt in range(1, 7):
        try:
            _run(work)
            break
        except LockNotAvailable:
            print(f"  Rows locked by a concurrent writer (attempt {attempt}); "
                  "retrying in 30 s...")
            time.sleep(30)
    else:
        raise SystemExit("  Could not acquire row locks; nothing was written.")
    print(f"\n  Applied {len(changes)} row updates and {len(renames)} renames.")


if __name__ == "__main__":
    ch = plan()
    report(ch)
    if "--apply" in sys.argv:
        backup()
        apply(ch)
    else:
        print("\n  Dry run only -- nothing written. Re-run with --apply to commit.")
