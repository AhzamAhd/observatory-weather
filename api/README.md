# GOWC API (Phase 1 backend)

A FastAPI JSON API that wraps GOWC's existing Python logic modules
(`observing_engine`, `ads_search`, `transients`, `db`, …) and reads the same
Supabase database. It is a **separate application** from the Streamlit app —
running it does not touch `dashboard.py` or how Streamlit is deployed. Both can
run side by side against the same DB.

This is Phase 1 of the production rebuild: the backend. A frontend (Next.js
PWA) will consume this API in a later phase. The Streamlit app stays live and
unchanged throughout.

## Run locally

```bash
cd api
pip install -r requirements.txt          # plus the repo-root requirements (shared modules)
uvicorn main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** — FastAPI auto-generates interactive
API documentation for every endpoint.

## Environment

The API reuses the same secrets as the Streamlit app (read from environment
variables):

- `SUPABASE_DB_HOST`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_PORT`
  — the database (required for observatory/observe endpoints).
- `ADS_API_TOKEN` — NASA ADS (required for `/literature/search`).
- `GOWC_CORS_ORIGINS` — comma-separated allowed origins for the browser
  frontend (default `*`; tighten to the real frontend domain in production).

Never commit these — set them in the environment / deploy platform.

## Endpoints

| Method | Path | What |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/observatories?limit=&min_score=` | Latest conditions, best score first |
| GET | `/observatories/{id}` | One observatory's latest reading |
| GET | `/observe/rank?target=&ra=&dec=&date=` | Rank sites for a target (real engine, no LLM) |
| GET | `/transients/classes` | Target classes + which have live data |
| GET | `/transients/targets?target_class=` | Targets for a class (catalogue + live alerts) |
| GET | `/literature/search?q=&rows=&sort=&year_min=&year_max=` | Real NASA ADS papers (no LLM) |

## Guarantees carried over from the modules

- **No LLM in the paper path** — `/literature/search` returns verbatim ADS data.
- **Engine numbers are deterministic** — `/observe/rank` computes real
  observability via ephem; no fabrication.

## Deploy (later)

Deploy as a separate service (Render/Fly/Railway) with the same env vars. The
start command is `uvicorn main:app --host 0.0.0.0 --port $PORT`. It does not
interfere with the Streamlit service.
