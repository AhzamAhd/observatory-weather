"""
Country lookup for observatory coordinates.

Point-in-polygon against Natural Earth 1:50m admin-0 country borders (public
domain; https://www.naturalearthdata.com), with a nearest-border fallback for
coastal and island sites that fall just outside the generalised coastline.
Replaces the old rough latitude/longitude boxes, which overlapped (Peru fell in
the "Brazil" box, northern Chile in "Argentina") and left most sites "Unknown".

Pure Python + numpy; the GeoJSON is downloaded once and cached in data/.
"""
import json
import math
import os

import numpy as np
import requests

_NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
           "v5.1.2/geojson/ne_50m_admin_0_countries.geojson")
_NE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "ne_50m_admin_0_countries.geojson")
_MAX_FALLBACK_DEG = 1.0   # coastal/island sites: nearest border within ~100 km

_countries = None   # list of (name, [(ring_lon, ring_lat, bbox), ...])


def _load():
    global _countries
    if _countries is not None:
        return _countries
    if not os.path.exists(_NE_PATH):
        os.makedirs(os.path.dirname(_NE_PATH), exist_ok=True)
        r = requests.get(_NE_URL, timeout=60)
        r.raise_for_status()
        with open(_NE_PATH, "wb") as f:
            f.write(r.content)
    with open(_NE_PATH, encoding="utf-8") as f:
        features = json.load(f)["features"]

    _countries = []
    for feat in features:
        name = feat["properties"]["NAME"]
        geom = feat["geometry"]
        polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                 else [geom["coordinates"]])
        rings = []
        for poly in polys:
            outer = np.asarray(poly[0], dtype=float)   # holes ignored: none matter here
            lon, lat = outer[:, 0], outer[:, 1]
            rings.append((lon, lat, (lon.min(), lon.max(), lat.min(), lat.max())))
        _countries.append((name, rings))
    return _countries


def _inside(lon, lat, rlon, rlat):
    """Even-odd ray casting for one ring."""
    x0, y0 = rlon, rlat
    x1, y1 = np.roll(rlon, -1), np.roll(rlat, -1)
    crosses = (y0 > lat) != (y1 > lat)
    with np.errstate(divide="ignore", invalid="ignore"):
        xint = x0 + (lat - y0) * (x1 - x0) / (y1 - y0)
    return bool(np.count_nonzero(crosses & (lon < xint)) % 2)


def country_for(lat, lon):
    """Country name for a coordinate, or "Unknown" (open ocean / >~100 km out)."""
    if lat is None or lon is None:
        return "Unknown"
    lat, lon = float(lat), float(lon)
    best_name, best_d = None, _MAX_FALLBACK_DEG
    coslat = max(0.1, math.cos(math.radians(lat)))
    for name, rings in _load():
        for rlon, rlat, (x0, x1, y0, y1) in rings:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and _inside(lon, lat, rlon, rlat):
                return name
            # cheap bbox gate before the vertex-distance fallback
            if (x0 - best_d / coslat <= lon <= x1 + best_d / coslat
                    and y0 - best_d <= lat <= y1 + best_d):
                d = np.min(np.hypot((rlon - lon) * coslat, rlat - lat))
                if d < best_d:
                    best_name, best_d = name, d
    return best_name or ("Antarctica" if lat < -60 else "Unknown")
