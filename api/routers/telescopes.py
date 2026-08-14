"""Telescope-efficiency endpoint — wraps telescope_efficiency.py.

Efficiency ratings per observatory for a telescope type (optical / infrared /
radio), based on live conditions. Real computation, no LLM."""
import math

from fastapi import APIRouter, HTTPException, Query

from telescope_efficiency import get_all_efficiency_scores

router = APIRouter(prefix="/telescopes", tags=["telescopes"])

VALID_TYPES = ["optical", "infrared", "radio"]


def _clean(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None
        elif k == "fetch_datetime" and v is not None:
            out[k] = str(v)
        else:
            out[k] = v
    return out


@router.get("/efficiency")
def efficiency(
    telescope_type: str = Query("optical"),
    limit: int = Query(100, ge=1, le=500),
):
    """Efficiency ratings for all observatories, best first."""
    if telescope_type not in VALID_TYPES:
        raise HTTPException(400, f"telescope_type must be one of {VALID_TYPES}")
    try:
        df = get_all_efficiency_scores(telescope_type)
    except Exception as e:
        raise HTTPException(502, f"Computation error: {type(e).__name__}")
    if df is None or df.empty:
        return {"telescope_type": telescope_type, "count": 0, "sites": []}

    df = df.sort_values("efficiency_score", ascending=False)
    rows = [_clean(r) for r in df.head(limit).to_dict("records")]
    return {"telescope_type": telescope_type, "count": len(rows), "sites": rows}
