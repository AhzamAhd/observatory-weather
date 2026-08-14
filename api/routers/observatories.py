"""Observatory + live-weather endpoints — wraps db.py queries.

The headline observation_score here is GOWC's GENUINE multiplicative
observing-quality index (the same one the Streamlit app shows), not a raw
cloud-only proxy. Both apps must agree, so this reuses atmospheric.py exactly
as dashboard.py does."""
from fastapi import APIRouter, HTTPException, Query

import db
from atmospheric import (calculate_seeing, calculate_jet_stream_impact,
                        observing_quality_score, observing_condition)

router = APIRouter(prefix="/observatories", tags=["observatories"])

# The same "latest reading per observatory" query the Streamlit app uses. The
# SQL score is the WEATHER component only; the real index is computed below.
_LATEST_SQL = """
    SELECT DISTINCT ON (o.id)
        o.id, o.name AS observatory, o.country, o.latitude, o.longitude,
        o.altitude_m, o.mpc_code,
        w.fetch_datetime, w.cloud_cover_pct, w.humidity_pct, w.wind_speed_ms,
        w.temperature_c, w.precipitation_mm, w.surface_pressure, w.jet_stream_ms
    FROM weather_readings w
    JOIN observatories o ON w.observatory_id = o.id
    WHERE w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
    ORDER BY o.id, w.fetch_datetime DESC
"""


def _real_score(r):
    """GOWC's genuine multiplicative observing-quality index — identical to
    the Streamlit app's headline score (atmospheric.observing_quality_score)."""
    seeing = calculate_seeing(
        r.get("temperature_c"), r.get("wind_speed_ms"),
        r.get("humidity_pct"), r.get("altitude_m") or 0)
    _, jet_impact = calculate_jet_stream_impact(
        r.get("jet_stream_ms"), r.get("latitude") or 0)
    return observing_quality_score(
        r.get("cloud_cover_pct"), r.get("humidity_pct"),
        r.get("wind_speed_ms"), r.get("precipitation_mm"),
        seeing, jet_impact)


@router.get("")
def list_observatories(
    limit: int = Query(200, ge=1, le=2000),
    min_score: float = Query(None, ge=0, le=100),
):
    """Latest conditions for observatories, best score first. Uses GOWC's
    genuine observing-quality index."""
    try:
        df = db.query_df(_LATEST_SQL)
    except Exception as e:
        raise HTTPException(502, f"Database error: {type(e).__name__}")
    if df.empty:
        return {"count": 0, "observatories": []}

    df["observation_score"] = df.apply(_real_score, axis=1)
    df["condition"] = df["observation_score"].apply(observing_condition)
    df = df.sort_values("observation_score", ascending=False)
    if min_score is not None:
        df = df[df["observation_score"] >= min_score]
    rows = df.head(limit).to_dict("records")
    for r in rows:
        if r.get("fetch_datetime") is not None:
            r["fetch_datetime"] = str(r["fetch_datetime"])
    return {"count": len(rows), "observatories": rows}


_ONE_SQL = """
    SELECT o.id, o.name AS observatory, o.country, o.latitude, o.longitude,
        o.altitude_m, o.mpc_code,
        w.fetch_datetime, w.cloud_cover_pct, w.humidity_pct, w.wind_speed_ms,
        w.temperature_c, w.precipitation_mm, w.surface_pressure, w.jet_stream_ms
    FROM weather_readings w
    JOIN observatories o ON w.observatory_id = o.id
    WHERE o.id = %s
    ORDER BY w.fetch_datetime DESC
    LIMIT 1
"""


@router.get("/{observatory_id}")
def get_observatory(observatory_id: int):
    """One observatory's latest reading by id, with the genuine score."""
    try:
        row = db.fetch_one(_ONE_SQL, (observatory_id,))
    except Exception as e:
        raise HTTPException(502, f"Database error: {type(e).__name__}")
    if not row:
        raise HTTPException(404, "Observatory not found")
    row["observation_score"] = _real_score(row)
    row["condition"] = observing_condition(row["observation_score"])
    if row.get("fetch_datetime") is not None:
        row["fetch_datetime"] = str(row["fetch_datetime"])
    return row
