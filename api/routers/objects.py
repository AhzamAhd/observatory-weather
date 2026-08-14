"""Object-visibility endpoints — wraps object_visibility.py.

Given a catalogue object (galaxy, nebula, planet, star…), returns which
observatories can see it now, with altitude/airmass. Real ephem computation,
no LLM."""
import math

from fastapi import APIRouter, HTTPException, Query

import db
from object_visibility import (OBJECTS, get_best_observatories_for_object,
                               calculate_visibility)

router = APIRouter(prefix="/objects", tags=["objects"])

_OBS_SQL = """
    SELECT DISTINCT ON (o.id) o.name AS observatory, o.country, o.latitude,
        o.longitude, o.altitude_m,
        ROUND(GREATEST(0, 100 - (w.cloud_cover_pct * 0.50))::numeric, 1)
            AS observation_score
    FROM weather_readings w JOIN observatories o ON w.observatory_id = o.id
    WHERE w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
    ORDER BY o.id, w.fetch_datetime DESC
"""


def _clean(row: dict) -> dict:
    return {
        k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
        for k, v in row.items()
    }


@router.get("/catalog")
def catalog(q: str = Query(None, description="Optional name filter."),
            limit: int = Query(100, ge=1, le=400)):
    """List catalogue objects (name + type). Optional substring filter."""
    items = [{"name": name, "type": meta.get("type", "object")}
             for name, meta in OBJECTS.items()]
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it["name"].lower()]
    # group-friendly sort: by type then name
    items.sort(key=lambda it: (it["type"], it["name"]))
    return {"count": len(items), "objects": items[:limit]}


@router.get("/visibility")
def visibility(object_name: str = Query(..., description="Exact catalogue name.")):
    """Best observatories to see this object right now, ranked."""
    if object_name not in OBJECTS:
        # help the caller with near matches
        ql = object_name.lower()
        near = [n for n in OBJECTS if ql in n.lower()][:8]
        raise HTTPException(404, {"message": f"Unknown object '{object_name}'.",
                                  "candidates": near})
    import pandas as pd
    try:
        df = db.query_df(_OBS_SQL)
    except Exception as e:
        raise HTTPException(502, f"Database error: {type(e).__name__}")
    if df.empty:
        return {"object": object_name, "sites": []}

    result = get_best_observatories_for_object(object_name, df)
    if not isinstance(result, pd.DataFrame) or result.empty:
        return {"object": object_name, "sites": [],
                "message": "Not visible from any tracked site right now."}
    rows = [_clean(r) for r in result.head(25).to_dict("records")]
    return {"object": object_name, "count": len(rows), "sites": rows}
