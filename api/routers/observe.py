"""Observing-engine endpoints — wraps observing_engine.rank_sites."""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

import db
from observing_engine import (rank_sites, resolve_target, resolve_solar_system,
                              find_targets)

router = APIRouter(prefix="/observe", tags=["observe"])

_WX_SQL = """
    SELECT DISTINCT ON (o.id) o.latitude, o.longitude,
        ROUND(GREATEST(0, 100 - (w.cloud_cover_pct * 0.50))::numeric, 1)
            AS observation_score
    FROM weather_readings w JOIN observatories o ON w.observatory_id = o.id
    WHERE w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
    ORDER BY o.id, w.fetch_datetime DESC
"""


def _weather_rows():
    try:
        df = db.query_df(_WX_SQL)
        return df.to_dict("records") if not df.empty else []
    except Exception:
        return []


@router.get("/rank")
def rank(
    target: str = Query(None, description="Target name (e.g. 'Sco X-1', "
                        "'the Moon'). Provide this OR ra+dec."),
    ra: float = Query(None, description="RA in decimal degrees."),
    dec: float = Query(None, description="Dec in decimal degrees."),
    date: str = Query(None, description="Observing date YYYY-MM-DD (default: today UTC)."),
):
    """Rank observatories for a target on a date. Real engine numbers only —
    no LLM. Accepts a named target (resolved from GOWC's catalogues / solar
    system) or explicit RA/Dec."""
    date_utc = None
    if date:
        try:
            date_utc = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "date must be YYYY-MM-DD")

    body_cls = None
    if ra is None or dec is None:
        if not target:
            raise HTTPException(400, "Provide a target name or ra+dec.")
        body_cls = resolve_solar_system(target)
        if body_cls is None:
            coords = resolve_target(target)
            if coords is None:
                # offer candidates instead of a bare 404
                cands = find_targets(target)
                raise HTTPException(
                    404,
                    {"message": f"Couldn't resolve '{target}'.",
                     "candidates": [c["display"] for c in cands]})
            ra, dec = coords

    result = rank_sites(ra, dec, date_utc, weather_rows=_weather_rows(),
                        body_cls=body_cls)
    if body_cls is not None:
        result["target"] = {"name": target}
    return result
