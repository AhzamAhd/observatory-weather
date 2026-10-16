from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sqlite3
import pandas as pd
from datetime import datetime
from atmospheric import (get_full_atmospheric_analysis,
                          observing_quality_score, observing_condition)

# ── App setup ─────────────────────────────────────────────────────
app = FastAPI(
    title="Global Observing-conditions Weather Catalogue API",
    description="""
## 🔭 Global Observing-conditions Weather Catalogue API

Live atmospheric conditions and observation quality scores
for 2,600+ catalogued observatory sites worldwide.

### What you can do
- Get current observation quality scores for all observatories
- Find the best observatory in the world right now
- Get detailed atmospheric data including seeing, PWV, jet stream
- Filter by country or minimum score
- Get data for a specific observatory by name

### Data sources
- Weather data: [Open-Meteo](https://open-meteo.com) — free, open source
- Observatory list: [Minor Planet Center](https://minorplanetcenter.net)
- Pipeline runs daily at 06:00 UTC via GitHub Actions

### Score interpretation
| Score | Condition | Meaning |
|-------|-----------|---------|
| 80–100 | Excellent | Perfect observing night |
| 60–79 | Good | Minor atmospheric interference |
| 40–59 | Marginal | Bright targets only |
| 0–39 | Poor | Dome should be closed |
    """,
    version="1.0.0",
    contact={
        "name": "Ahzam Ahmed",
        "url": "https://github.com/AhzamAhd/observatory-weather"
    },
    license_info={
        "name": "MIT"
    }
)

# ── CORS — allow anyone to call this API ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"]
)

# ── Database helper ───────────────────────────────────────────────
from db import query_df

def _add_real_scores(df):
    """Replace the placeholder query ordering with the genuine, physics-based
    observing_quality_score (same multiplicative model the dashboard shows --
    clarity/dryness/dew/wind/seeing/jet/precipitation -- atmospheric.py). The
    SQL in scores_query() no longer computes a score at all; this is the one
    place observation_score/condition are produced, so the API and dashboard
    can never again disagree on what a site's score is.
    """
    if df.empty:
        df["observation_score"] = []
        df["condition"] = []
        return df

    def _score_row(r):
        atm = get_full_atmospheric_analysis(r)
        return observing_quality_score(
            r.get("cloud_cover_pct"), r.get("humidity_pct"),
            r.get("wind_speed_ms"), r.get("precipitation_mm"),
            atm["seeing_arcsec"], atm["jet_impact"],
            r.get("temperature_c"), r.get("dewpoint_c"))

    df["observation_score"] = df.apply(_score_row, axis=1)
    df["condition"] = df["observation_score"].apply(observing_condition)
    return df.sort_values("observation_score", ascending=False)


def scores_query(extra_where="", extra_params=None,
                 limit=None):
    params = extra_params or []
    sql    = f"""
        SELECT
            o.name          AS observatory,
            o.country,
            o.altitude_m,
            o.latitude,
            o.longitude,
            o.mpc_code,
            w.fetch_date,
            w.fetch_time,
            w.fetch_datetime,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            w.dewpoint_c,
            w.precipitation_mm,
            w.surface_pressure,
            w.jet_stream_ms,
            w.temp_850hpa,
            w.temp_700hpa,
            w.temp_600hpa,
            w.temp_500hpa,
            w.geopot_850hpa,
            w.geopot_700hpa,
            w.geopot_600hpa,
            w.geopot_500hpa,
            w.wind_850hpa,
            w.wind_700hpa,
            w.wind_600hpa,
            w.wind_500hpa,
            w.rh_850hpa,
            w.rh_500hpa,
            w.pwv_column,
            w.model_elevation_m
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        WHERE w.fetch_date = (
            SELECT MAX(fetch_date) FROM weather_readings
        )
        {extra_where}
    """
    df = _add_real_scores(query_df(sql, params))
    return df.head(limit) if limit else df

# ── Root endpoint ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["Info"])
def root():
    return """
    <html>
    <head>
        <title>GOWC API</title>
        <style>
            body { font-family: Arial, sans-serif;
                   background: #0E1117; color: #FAFAFA;
                   padding: 40px; max-width: 800px;
                   margin: 0 auto; }
            h1   { color: #1D9E75; }
            a    { color: #378ADD; }
            code { background: #1A1D24; padding: 2px 6px;
                   border-radius: 4px; }
            .endpoint { background: #1A1D24;
                        padding: 12px; border-radius: 8px;
                        margin: 8px 0; }
        </style>
    </head>
    <body>
        <h1>🔭 Global Observing-conditions Weather Catalogue API</h1>
        <p>Live atmospheric conditions for 2,600+ catalogued observatory sites worldwide.</p>
        <h2>Quick start</h2>
        <div class="endpoint">
            <code>GET /observatories/scores</code>
            — All observatory scores right now
        </div>
        <div class="endpoint">
            <code>GET /observatories/best?limit=10</code>
            — Top 10 sites tonight
        </div>
        <div class="endpoint">
            <code>GET /observatories/search?name=mauna</code>
            — Search by name
        </div>
        <div class="endpoint">
            <code>GET /observatories/country/Chile</code>
            — All observatories in a country
        </div>
        <div class="endpoint">
            <code>GET /atmospheric/scores</code>
            — Seeing, PWV and jet stream for all sites
        </div>
        <p>
            <a href="/docs">📖 Interactive API docs</a> ·
            <a href="/redoc">📚 ReDoc documentation</a>
        </p>
        <p style="color:#888; font-size:12px;">
            Data updated daily at 06:00 UTC ·
            Source: Open-Meteo + MPC
        </p>
    </body>
    </html>
    """

# ── Observatory endpoints ─────────────────────────────────────────
@app.get("/observatories", tags=["Observatories"])
def get_all_observatories():
    df = query_df("""
        SELECT name, country, latitude, longitude,
               altitude_m, mpc_code
        FROM observatories
        ORDER BY name
    """)
    return {
        "count":         len(df),
        "observatories": df.to_dict("records"),
        "updated_at":    datetime.utcnow().isoformat()
    }

@app.get("/observatories/scores", tags=["Scores"])
def get_all_scores():
    """
    Get current observation quality scores
    for all catalogued observatories, ranked best to worst.
    """
    df = scores_query()
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No score data found. "
                   "Run the pipeline first."
        )
    return {
        "count":      len(df),
        "updated_at": datetime.utcnow().isoformat(),
        "scores":     df.to_dict("records")
    }

@app.get("/observatories/best", tags=["Scores"])
def get_best_observatories(
    limit: int = Query(
        default=10, ge=1, le=3000,
        description="Number of results to return"
    ),
    min_score: float = Query(
        default=0, ge=0, le=100,
        description="Minimum observation score filter"
    )
):
    """
    Get the best observatories right now,
    optionally filtered by minimum score.
    """
    # min_score filters on the genuine observing_quality_score, which
    # scores_query() now computes in Python after the SQL fetch -- so filter
    # here rather than pushing a (now nonexistent) score column into SQL.
    df = scores_query()
    df = df[df["observation_score"] >= min_score]
    if limit:
        df = df.head(limit)
    return {
        "count":      len(df),
        "limit":      limit,
        "min_score":  min_score,
        "updated_at": datetime.utcnow().isoformat(),
        "scores":     df.to_dict("records")
    }

@app.get("/observatories/search", tags=["Observatories"])
def search_observatories(
    name: str = Query(
        description="Observatory name to search for"
    )
):
    """
    Search for an observatory by name.
    Partial matches work — try 'mauna' or 'chile'.
    """
    df = scores_query(
        extra_where="AND LOWER(o.name) LIKE LOWER(%s)",
        extra_params=[f"%{name}%"]
    )
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No observatory found matching '{name}'"
        )
    return {
        "count":      len(df),
        "query":      name,
        "updated_at": datetime.utcnow().isoformat(),
        "results":    df.to_dict("records")
    }

@app.get("/observatories/country/{country}",
         tags=["Observatories"])
def get_by_country(country: str):
    """
    Get all observatories in a specific country.
    Examples: Chile, USA, Spain, India, Australia
    """
    df = scores_query(
        extra_where="AND LOWER(o.country) LIKE LOWER(%s)",
        extra_params=[f"%{country}%"]
    )
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No observatories found in '{country}'"
        )
    return {
        "country":    country,
        "count":      len(df),
        "updated_at": datetime.utcnow().isoformat(),
        "results":    df.to_dict("records")
    }

@app.get("/observatories/condition/{condition}",
         tags=["Scores"])
def get_by_condition(
    condition: str
):
    """
    Get all observatories with a specific condition.
    Values: Excellent, Good, Marginal, Poor
    """
    valid = ["excellent", "good", "marginal", "poor"]
    if condition.lower() not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition. "
                   f"Use: Excellent, Good, Marginal, Poor"
        )
    # Filter on the genuine condition (derived from observing_quality_score
    # in Python by scores_query()) rather than a duplicated SQL CASE on the
    # old placeholder formula.
    df = scores_query()
    df = df[df["condition"] == condition.capitalize()]
    return {
        "condition":  condition.capitalize(),
        "count":      len(df),
        "updated_at": datetime.utcnow().isoformat(),
        "results":    df.to_dict("records")
    }

# ── Atmospheric endpoints ─────────────────────────────────────────
@app.get("/atmospheric/scores", tags=["Atmospheric"])
def get_atmospheric_scores():
    """
    Get seeing index, PWV, and jet stream impact
    for all observatories. Essential for professional
    telescope scheduling.
    """
    df      = scores_query()
    results = []

    for _, row in df.iterrows():
        atm = get_full_atmospheric_analysis(row)
        results.append({
            "observatory":      row["observatory"],
            "country":          row["country"],
            "altitude_m":       row["altitude_m"],
            "observation_score": row["observation_score"],
            "seeing_arcsec":    atm["seeing_arcsec"],
            "seeing_quality":   atm["seeing_quality"],
            "pwv_mm":           atm["pwv_mm"],
            "pwv_quality":      atm["pwv_quality"],
            "jet_stream_ms":    atm["jet_stream_ms"],
            "jet_impact":       atm["jet_impact"],
            "updated_at":       row.get("fetch_datetime")
        })

    results.sort(key=lambda x: x["seeing_arcsec"] or 99)

    return {
        "count":      len(results),
        "updated_at": datetime.utcnow().isoformat(),
        "results":    results
    }

@app.get("/atmospheric/best-seeing", tags=["Atmospheric"])
def get_best_seeing(
    limit: int = Query(default=10, ge=1, le=3000)
):
    """
    Get observatories ranked by best atmospheric seeing.
    Lower arcseconds = sharper images.
    """
    df      = scores_query()
    results = []

    for _, row in df.iterrows():
        atm = get_full_atmospheric_analysis(row)
        if atm["seeing_arcsec"] is not None:
            results.append({
                "observatory":   row["observatory"],
                "country":       row["country"],
                "altitude_m":    row["altitude_m"],
                "seeing_arcsec": atm["seeing_arcsec"],
                "seeing_quality": atm["seeing_quality"],
                "pwv_mm":        atm["pwv_mm"],
                "observation_score": row["observation_score"]
            })

    results.sort(key=lambda x: x["seeing_arcsec"])
    return {
        "count":      min(limit, len(results)),
        "updated_at": datetime.utcnow().isoformat(),
        "results":    results[:limit]
    }

@app.get("/atmospheric/best-pwv", tags=["Atmospheric"])
def get_best_pwv(
    limit: int = Query(default=10, ge=1, le=3000)
):
    """
    Get observatories ranked by lowest PWV.
    Critical for infrared and radio astronomy.
    Lower PWV = better IR/radio conditions.
    """
    df      = scores_query()
    results = []

    for _, row in df.iterrows():
        atm = get_full_atmospheric_analysis(row)
        if atm["pwv_mm"] is not None:
            results.append({
                "observatory":   row["observatory"],
                "country":       row["country"],
                "altitude_m":    row["altitude_m"],
                "pwv_mm":        atm["pwv_mm"],
                "pwv_quality":   atm["pwv_quality"],
                "seeing_arcsec": atm["seeing_arcsec"],
                "observation_score": row["observation_score"]
            })

    results.sort(key=lambda x: x["pwv_mm"])
    return {
        "count":      min(limit, len(results)),
        "updated_at": datetime.utcnow().isoformat(),
        "results":    results[:limit]
    }

# ── Stats endpoint ────────────────────────────────────────────────
@app.get("/stats", tags=["Info"])
def get_stats():
    """
    Get summary statistics for tonight's
    global observation conditions.
    """
    df = scores_query()
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No data available")

    return {
        "total_observatories": len(df),
        "excellent":  len(df[df["condition"] == "Excellent"]),
        "good":       len(df[df["condition"] == "Good"]),
        "marginal":   len(df[df["condition"] == "Marginal"]),
        "poor":       len(df[df["condition"] == "Poor"]),
        "avg_score":  round(
            df["observation_score"].mean(), 1),
        "best_site":  df.iloc[0]["observatory"],
        "best_score": df.iloc[0]["observation_score"],
        "worst_site": df.iloc[-1]["observatory"],
        "worst_score": df.iloc[-1]["observation_score"],
        "updated_at": datetime.utcnow().isoformat(),
        "data_date":  df.iloc[0]["fetch_date"]
    }

# ── Health check ──────────────────────────────────────────────────
@app.get("/health", tags=["Info"])
def health_check():
    try:
        df = query_df(
            "SELECT COUNT(*) AS count FROM observatories")
        return {
            "status":        "healthy",
            "observatories": int(df.iloc[0]["count"]),
            "timestamp":     datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)