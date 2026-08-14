"""Observatory + live-weather endpoints — wraps db.py queries."""
from fastapi import APIRouter, HTTPException, Query

import db

router = APIRouter(prefix="/observatories", tags=["observatories"])

# The same "latest reading per observatory" query the Streamlit app uses.
_LATEST_SQL = """
    SELECT DISTINCT ON (o.id)
        o.id, o.name AS observatory, o.country, o.latitude, o.longitude,
        o.altitude_m, o.mpc_code,
        w.fetch_datetime, w.cloud_cover_pct, w.humidity_pct, w.wind_speed_ms,
        w.temperature_c, w.precipitation_mm,
        ROUND(GREATEST(0, 100 - (w.cloud_cover_pct * 0.50))::numeric, 1)
            AS observation_score
    FROM weather_readings w
    JOIN observatories o ON w.observatory_id = o.id
    WHERE w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
    ORDER BY o.id, w.fetch_datetime DESC
"""


@router.get("")
def list_observatories(
    limit: int = Query(200, ge=1, le=2000),
    min_score: float = Query(None, ge=0, le=100),
):
    """Latest conditions for observatories, best score first."""
    try:
        df = db.query_df(_LATEST_SQL)
    except Exception as e:
        raise HTTPException(502, f"Database error: {type(e).__name__}")
    if df.empty:
        return {"count": 0, "observatories": []}

    df = df.sort_values("observation_score", ascending=False)
    if min_score is not None:
        df = df[df["observation_score"] >= min_score]
    rows = df.head(limit).to_dict("records")
    # JSON-safe: stringify timestamps
    for r in rows:
        if r.get("fetch_datetime") is not None:
            r["fetch_datetime"] = str(r["fetch_datetime"])
    return {"count": len(rows), "observatories": rows}


_ONE_SQL = """
    SELECT o.id, o.name AS observatory, o.country, o.latitude, o.longitude,
        o.altitude_m, o.mpc_code,
        w.fetch_datetime, w.cloud_cover_pct, w.humidity_pct, w.wind_speed_ms,
        w.temperature_c, w.precipitation_mm,
        ROUND(GREATEST(0, 100 - (w.cloud_cover_pct * 0.50))::numeric, 1)
            AS observation_score
    FROM weather_readings w
    JOIN observatories o ON w.observatory_id = o.id
    WHERE o.id = %s
    ORDER BY w.fetch_datetime DESC
    LIMIT 1
"""


@router.get("/{observatory_id}")
def get_observatory(observatory_id: int):
    """One observatory's latest reading by id."""
    try:
        row = db.fetch_one(_ONE_SQL, (observatory_id,))
    except Exception as e:
        raise HTTPException(502, f"Database error: {type(e).__name__}")
    if not row:
        raise HTTPException(404, "Observatory not found")
    if row.get("fetch_datetime") is not None:
        row["fetch_datetime"] = str(row["fetch_datetime"])
    return row
