"""
Live measured seeing from public site monitors (DIMM).

For the few observatories that publish real-time DIMM seeing, GOWC shows the
MEASURED value rather than the modelled one --- a measurement always beats a
model. Currently ESO Paranal and La Silla (ESO Astronomical Site Monitor); other
public monitors can be added to SOURCES.

get_live_seeing(site_name) returns (seeing_arcsec, timestamp_utc) for the most
recent measurement within the last few days, or None if the site has no monitor
or the query fails --- callers then fall back to the modelled seeing.
"""
import requests
from datetime import datetime, timedelta

# ESO ASM DIMM query endpoints (legacy wdb interface, returns CSV).
# Matched to a GOWC observatory by a name substring. Only Paranal exposes a
# programmatic DIMM-seeing table (dimm_paranal); La Silla's DIMM is not available
# through the query API (only its meteo table is), so it is not listed here and
# falls back to the model. Add more sites as public seeing APIs are found.
_ESO_BASE = "http://archive.eso.org/wdb/wdb/asm/{table}/query"
SOURCES = {
    "Paranal": {"table": "dimm_paranal"},
}

_TIMEOUT = 20
_CACHE = {}          # (site) -> (fetched_at, result)
_CACHE_TTL = 1800    # seconds; measurements update every ~1-2 min but we cache
                     # 30 min to avoid hammering ESO on every page load.


def _match_source(site_name):
    """Return the SOURCES entry whose key is a substring of site_name, or None."""
    if not site_name:
        return None
    low = site_name.lower()
    for key, cfg in SOURCES.items():
        if key.lower() in low:
            return key, cfg
    return None


def _fetch_eso_dimm(table):
    """Query ESO's ASM for the most recent DIMM seeing. Returns
    (seeing_arcsec, timestamp) or None."""
    end = datetime.utcnow()
    start = end - timedelta(days=3)
    rng = f"{start.strftime('%Y-%m-%d')}..{end.strftime('%Y-%m-%d')}"
    params = {
        "wdbo": "csv/download",
        "max_rows_returned": 50000,
        "tab_fwhm": "on",
        "start_date": rng,
        "order": "start_date",
    }
    r = requests.get(_ESO_BASE.format(table=table), params=params,
                     timeout=_TIMEOUT)
    r.raise_for_status()
    latest = None
    for line in r.text.splitlines():
        if not line or line.startswith("#") or line.startswith("Date"):
            continue
        parts = line.split(",")
        if len(parts) < 2 or not parts[1]:
            continue
        try:
            val = float(parts[1])
        except ValueError:
            continue
        if val > 0:                       # 0 = invalid/no measurement
            latest = (val, parts[0])      # rows are date-ordered; keep the last
    return latest


def get_live_seeing(site_name):
    """Measured DIMM seeing for `site_name` as (arcsec, timestamp_utc), or None
    if the site has no public monitor or the fetch fails. Cached per site."""
    src = _match_source(site_name)
    if not src:
        return None
    key, cfg = src

    now = datetime.utcnow().timestamp()
    cached = _CACHE.get(key)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]

    try:
        result = _fetch_eso_dimm(cfg["table"])
    except Exception:
        result = None                     # network/ESO error -> fall back to model
    # Cache even a None so a transient failure doesn't retry on every call.
    _CACHE[key] = (now, result)
    return result


def has_live_seeing(site_name):
    """True if `site_name` has a configured public DIMM monitor."""
    return _match_source(site_name) is not None


if __name__ == "__main__":
    for s in ("ESO Paranal Observatory (VLT)", "ESO La Silla Observatory",
              "Some Amateur Observatory"):
        res = get_live_seeing(s)
        if res:
            print(f"{s[:32]:32} MEASURED {res[0]}\" at {res[1]}")
        else:
            print(f"{s[:32]:32} no live monitor (use model)")
