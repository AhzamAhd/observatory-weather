"""
GOWC API — FastAPI backend (Phase 1 of the production rebuild).

This wraps GOWC's existing Python logic modules (observing_engine, ads_search,
transients, db, …) as a JSON HTTP API. It is a SEPARATE application from the
Streamlit app: it imports the same modules and reads the same Supabase DB, but
does not touch dashboard.py or how Streamlit runs. Both can run side by side.

Run locally:
    cd api
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
    # then open http://localhost:8000/docs  (auto-generated API docs)
"""
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import GOWC's existing modules from the repo root (one level up from api/).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from routers import (observatories, observe, transients_api, literature,  # noqa: E402
                     objects, sky_events, telescopes)

app = FastAPI(
    title="GOWC API",
    version="0.1.0",
    description="JSON API for the Global Observatory Weather Tracker. Wraps "
                "GOWC's existing engine, ADS search, transient catalogue and "
                "observatory data.",
)

# CORS: allow the future frontend (and local dev) to call this API from the
# browser. Tighten `allow_origins` to the real frontend domain before prod.
_origins = os.environ.get("GOWC_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    """Liveness probe."""
    return {"status": "ok", "service": "gowc-api", "version": app.version}


app.include_router(observatories.router)
app.include_router(observe.router)
app.include_router(transients_api.router)
app.include_router(literature.router)
app.include_router(objects.router)
app.include_router(sky_events.router)
app.include_router(telescopes.router)
