"""Observatory + live-weather endpoints — wraps db.py queries.

The headline observation_score here is GOWC's GENUINE multiplicative
observing-quality index (the same one the Streamlit app shows), not a raw
cloud-only proxy. Both apps must agree, so this reuses atmospheric.py exactly
as dashboard.py does."""
import math

from fastapi import APIRouter, HTTPException, Query

import db
from atmospheric import (calculate_seeing, calculate_jet_stream_impact,
                        observing_quality_score, observing_condition)


def _clean(row: dict) -> dict:
    """Replace NaN/Inf floats with None so the row is valid JSON.

    Some observatories have missing weather fields (e.g. jet_stream_ms) that
    come back as NaN from the DB/pandas; NaN is not valid JSON and makes the
    response serializer 500. Also stringify the timestamp."""
    out = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None
        else:
            out[k] = v
    if out.get("fetch_datetime") is not None:
        out["fetch_datetime"] = str(out["fetch_datetime"])
    return out

router = APIRouter(prefix="/observatories", tags=["observatories"])

# The same "latest reading per observatory" query the Streamlit app uses. The
# SQL score is the WEATHER component only; the real index is computed below.
_LATEST_SQL = """
    SELECT DISTINCT ON (o.id)
        o.id, o.name AS observatory, o.country, o.latitude, o.longitude,
        o.altitude_m, o.mpc_code,
        w.fetch_datetime, w.cloud_cover_pct, w.humidity_pct, w.wind_speed_ms,
        w.temperature_c, w.precipitation_mm, w.surface_pressure, w.jet_stream_ms,
        w.temp_850hpa, w.temp_500hpa, w.geopot_850hpa, w.geopot_500hpa, w.wind_850hpa
    FROM weather_readings w
    JOIN observatories o ON w.observatory_id = o.id
    WHERE w.fetch_date = (SELECT MAX(fetch_date) FROM weather_readings)
    ORDER BY o.id, w.fetch_datetime DESC
"""


def _real_score(r):
    """GOWC's genuine multiplicative observing-quality index — identical to
    the Streamlit app's headline score (atmospheric.observing_quality_score).
    Passes the vertical profile so seeing uses the Tatarski model when present."""
    profile = {
        "temp_850hpa":   r.get("temp_850hpa"),
        "temp_500hpa":   r.get("temp_500hpa"),
        "geopot_850hpa": r.get("geopot_850hpa"),
        "geopot_500hpa": r.get("geopot_500hpa"),
        "wind_850hpa":   r.get("wind_850hpa"),
        "jet_stream_ms": r.get("jet_stream_ms"),
    }
    seeing = calculate_seeing(
        r.get("temperature_c"), r.get("wind_speed_ms"),
        r.get("humidity_pct"), r.get("altitude_m") or 0,
        profile=profile)
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
    rows = [_clean(r) for r in df.head(limit).to_dict("records")]
    return {"count": len(rows), "observatories": rows}


_ONE_SQL = """
    SELECT o.id, o.name AS observatory, o.country, o.latitude, o.longitude,
        o.altitude_m, o.mpc_code,
        w.fetch_datetime, w.cloud_cover_pct, w.humidity_pct, w.wind_speed_ms,
        w.temperature_c, w.precipitation_mm, w.surface_pressure, w.jet_stream_ms,
        w.temp_850hpa, w.temp_500hpa, w.geopot_850hpa, w.geopot_500hpa, w.wind_850hpa
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
    return _clean(row)
