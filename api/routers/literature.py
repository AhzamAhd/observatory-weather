"""Literature-search endpoint — wraps ads_search.py (NASA ADS).

No LLM anywhere: every paper is verbatim ADS data (same guarantee as the
Streamlit tab)."""
from fastapi import APIRouter, HTTPException, Query

from ads_search import search_papers, ADSError, SORT_OPTIONS

router = APIRouter(prefix="/literature", tags=["literature"])


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Topic / keywords."),
    rows: int = Query(15, ge=1, le=20),
    sort: str = Query("Relevance"),
    year_min: int = Query(None, ge=1900, le=2100),
    year_max: int = Query(None, ge=1900, le=2100),
):
    """Search NASA ADS for real papers. Requires ADS_API_TOKEN on the server."""
    if sort not in SORT_OPTIONS:
        raise HTTPException(400, f"sort must be one of {list(SORT_OPTIONS)}")
    try:
        papers = search_papers(q, rows=rows, sort=sort,
                               year_min=year_min, year_max=year_max)
    except ADSError as e:
        raise HTTPException(502, str(e))
    return {"query": q, "count": len(papers), "papers": papers}
