# Observatory Weather Tracker
### Automated Observational Quality Pipeline — Python · SQLite · GitHub Actions

![Python](https://img.shields.io/badge/Python-3.11-blue) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Pipeline-Active-brightgreen)

---

## What this project does

This is a fully automated ETL (Extract, Transform, Load) data pipeline that fetches live atmospheric weather conditions from 5 of the world's most famous astronomical observatories every 24 hours. It calculates an **Observation Quality Score (0–100)** for each site based on real astronomy physics — cloud cover, humidity, and wind speed — stores the results in a structured SQLite database, generates professional charts, and commits everything back to GitHub automatically.

The entire pipeline runs for free using GitHub Actions with zero manual intervention required after setup.

---

## Why I built this

Most junior data projects stop at "I downloaded a CSV and made a chart." This project demonstrates the **full data engineering loop**:

- **Extraction** — calling a live REST API and handling real-world errors
- **Storage** — designing a relational schema and loading data into SQL
- **Transformation** — writing a domain-informed scoring algorithm in SQL
- **Automation** — scheduling daily runs with GitHub Actions (CI/CD)

It also applies real **astronomy domain knowledge**: the scoring formula is weighted based on how each atmospheric variable actually affects telescope performance.

---

## The 5 Observatories

| Observatory | Country | Altitude | Why it's famous |
|---|---|---|---|
| Mauna Kea Observatory | USA (Hawaii) | 4,205 m | Home to the largest optical telescopes on Earth |
| Paranal Observatory | Chile | 2,635 m | ESO's Very Large Telescope (VLT) site |
| La Palma Observatory | Spain (Canary Islands) | 2,396 m | Site of the Gran Telescopio Canarias |
| Cerro Pachón Observatory | Chile | 2,722 m | Future home of the Vera Rubin Observatory |
| Himalayan Chandra Telescope | India | 4,500 m | India's highest astronomical observatory |

---

## Tech stack

| Tool | Purpose | Why I chose it |
|---|---|---|
| Python 3.11 | Core language | Industry standard for data engineering |
| `requests` library | HTTP API calls | Simplest, most widely used HTTP library |
| Open-Meteo API | Weather data source | Free, no API key needed, excellent atmospheric detail |
| `sqlite3` (built-in) | Database | No setup needed; demonstrates SQL skills clearly |
| `pandas` | Data verification | Industry standard for tabular data analysis |
| `matplotlib` | Visualisation | Lightweight charting with no extra dependencies |
| GitHub Actions | Automation / scheduling | Free CI/CD; proves pipeline thinking |

---

## Project structure

```
observatory-weather/
│
├── data/
│   ├── bronze/                        # Raw API responses (JSON) — never modified
│   │   └── raw_weather_YYYY-MM-DD.json
│   ├── silver/                        # Cleaned and loaded into SQLite
│   │   └── observatory_weather.db
│   └── gold/                          # Scored output and charts
│       ├── observation_scores_YYYY-MM-DD.csv
│       └── charts/
│           ├── scores_bar_chart.png
│           └── weather_breakdown.png
│
├── .github/
│   └── workflows/
│       └── daily_fetch.yml            # GitHub Actions automation
│
├── fetch_weather.py                   # Phase 2 — Extract: calls API, saves JSON
├── load_database.py                   # Phase 3 — Load: reads JSON, inserts into SQLite
├── score_quality.py                   # Phase 4 — Transform: calculates observation scores
├── visualize.py                       # Phase 4 — Charts: bar + breakdown plots
│
├── requirements.txt                   # All Python dependencies
├── .gitignore                         # Excludes venv/, .env, __pycache__
└── README.md                          # This file
```

---

## The medallion architecture (Bronze → Silver → Gold)

This project follows the **medallion architecture** — a data engineering pattern used by companies like Databricks and Airbnb.

```
[Open-Meteo API]
      │
      ▼
  BRONZE layer          Raw JSON files, dated, never modified
  data/bronze/          One file per day: raw_weather_YYYY-MM-DD.json
      │
      ▼
  SILVER layer          Cleaned, structured, loaded into SQLite
  SQLite database       Deduplicated, typed, relational schema
      │
      ▼
  GOLD layer            Scored, analysed, visualised
  Observation scores    CSV + charts, ready for reporting
```

**Why this matters:** In production data engineering, you never transform raw data in place. Keeping Bronze untouched means you can always reprocess from source if your transformation logic changes.

---

## Phase 1 — Environment setup

Before writing any project code, the following foundation was established:

- Installed Python 3.11 and VS Code
- Created a virtual environment with `py -m venv venv` and activated it with `venv\Scripts\activate`
- Installed dependencies: `pip install requests pandas matplotlib`
- Saved dependencies with `pip freeze > requirements.txt`
- Created `.gitignore` to exclude `venv/`, `__pycache__/`, `*.pyc`, and `.env`
- Initialised a Git repo and pushed to GitHub

**What I learned:** Virtual environments isolate project dependencies so packages do not conflict across projects. The `.gitignore` file prevents sensitive files and large generated folders from being pushed to GitHub.

---

## Phase 2 — Data extraction (`fetch_weather.py`)

The fetcher loops through all 5 observatories and calls the Open-Meteo API for each one using its latitude and longitude. No API key is required.

**What data is collected per observatory:**

| Field | Unit | What it means |
|---|---|---|
| `cloud_cover_pct` | % (0–100) | Percentage of sky covered by cloud |
| `humidity_pct` | % (0–100) | Relative humidity at 2 metres above ground |
| `wind_speed_ms` | m/s | Wind speed at 10 metres above ground |
| `temperature_c` | °C | Air temperature |
| `precipitation_mm` | mm | Rainfall or snowfall in the last hour |
| `timestamp_utc` | ISO 8601 | Exact time the data was fetched |

**Key engineering decisions:**

- `try/except` error handling — if one observatory's API call fails, the script skips it and continues rather than crashing
- `raise_for_status()` — cleanly catches bad HTTP responses (404, 500) without extra if statements
- Dated filenames (`raw_weather_2026-04-21.json`) — preserves a full history of raw data
- Wind speed in m/s — more precise than km/h for astronomy applications
- Data saved to `data/bronze/` — the raw, unmodified Bronze layer

**Sample output:**
```
Starting weather fetch — 2026-04-21 06:00 UTC

  Fetching → Mauna Kea Observatory...
  Done      cloud=0.0%  humidity=74.0%  wind=2.11 m/s
  Fetching → Paranal Observatory...
  Done      cloud=22.0%  humidity=63.0%  wind=0.91 m/s
  Fetching → La Palma Observatory...
  Done      cloud=47.0%  humidity=87.0%  wind=1.39 m/s
  Fetching → Cerro Pachon Observatory...
  Done      cloud=0.0%  humidity=36.0%  wind=3.44 m/s
  Fetching → Himalayan Chandra Telescope...
  Done      cloud=0.0%  humidity=34.0%  wind=1.4 m/s

Saved 5 records → data/bronze/raw_weather_2026-04-21.json
```

---

## Phase 3 — Database storage (`load_database.py`)

The SQLite database has two tables linked by a foreign key — a proper relational design.

```sql
-- Table 1: Static observatory metadata
CREATE TABLE IF NOT EXISTS observatories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    country     TEXT,
    latitude    REAL,
    longitude   REAL,
    altitude_m  INTEGER,
    UNIQUE(name)
);

-- Table 2: Daily weather readings
CREATE TABLE IF NOT EXISTS weather_readings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    observatory_id      INTEGER REFERENCES observatories(id),
    timestamp_utc       TEXT,
    cloud_cover_pct     REAL,
    humidity_pct        REAL,
    wind_speed_ms       REAL,
    temperature_c       REAL,
    precipitation_mm    REAL,
    UNIQUE(observatory_id, timestamp_utc)
);
```

**Key engineering decisions:**

- `INSERT OR IGNORE` — safely skips duplicate rows without crashing
- `UNIQUE(observatory_id, timestamp_utc)` — prevents the same reading being inserted twice
- Parameterised queries (`?` placeholders) — prevents SQL injection, a real security habit
- Foreign key linking the two tables — proper relational database design
- Database stored in `data/silver/` — the cleaned Silver layer

**What I learned:** Moving data from a JSON file into a SQL database is what separates a data engineer from an analyst. The relational schema means you can JOIN tables, filter by date, and query across observatories with a single SQL statement.

---

## Phase 4 — Transformation and scoring (`score_quality.py`)

The scoring formula is based on real astronomy physics. Three atmospheric variables affect telescope performance:

| Variable | Weight | Why |
|---|---|---|
| Cloud cover | 50% | Clouds block all optical observation entirely |
| Humidity | 30% | Above 85% causes condensation on mirror surfaces |
| Wind speed | 20% | Above 15 m/s causes telescope vibration and poor tracking |

**The SQL scoring formula:**

```sql
ROUND(
    MAX(0,
        100
        - (w.cloud_cover_pct * 0.50)
        - (CASE
            WHEN w.humidity_pct > 85
            THEN (w.humidity_pct - 85) * 2.0
            ELSE 0
           END)
        - (CASE
            WHEN w.wind_speed_ms > 15
            THEN (w.wind_speed_ms - 15) * 2.0
            ELSE 0
           END)
    )
, 1) AS observation_score
```

**Score interpretation:**

| Score | Condition | Meaning |
|---|---|---|
| 80 – 100 | Excellent | Perfect observing night |
| 60 – 79 | Good | Minor atmospheric interference |
| 40 – 59 | Marginal | Usable but not ideal |
| 0 – 39 | Poor | Telescope should not operate |

**Real results from 2026-04-21:**

```
Mauna Kea Observatory      100.0 / 100  [Excellent]
Cerro Pachon Observatory   100.0 / 100  [Excellent]
Himalayan Chandra          100.0 / 100  [Excellent]
Paranal Observatory         89.0 / 100  [Excellent]
La Palma Observatory        72.5 / 100  [Good]
```

La Palma scored lower because its humidity of 87% crossed the 85% penalty threshold and it had 47% cloud cover — the formula correctly identified it as the worst site that night.

---

## Phase 4 — Visualisation (`visualize.py`)

Two charts are generated automatically on every pipeline run and saved to `data/gold/charts/`:

**Chart 1 — Observation Quality Bar Chart**
A horizontal bar chart showing each observatory's score, colour-coded by condition (green = Excellent, blue = Good, amber = Marginal, red = Poor).

**Chart 2 — Weather Breakdown**
Three side-by-side bar charts showing cloud cover, humidity, and wind speed for each observatory, with red dashed threshold lines at the penalty boundaries (85% humidity, 15 m/s wind).

---

## Phase 5 — Automation (`daily_fetch.yml`)

The pipeline runs automatically every day at 06:00 UTC via GitHub Actions.

```yaml
name: Daily Observatory Weather Pipeline

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python fetch_weather.py
      - run: python load_database.py
      - run: python score_quality.py
      - run: python visualize.py
      - name: Commit results to repo
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "actions@github.com"
          git add data/
          git diff --staged --quiet || git commit -m "auto: daily weather update $(date -u '+%Y-%m-%d')"
          git push
```

**Important setup step:** GitHub repo → Settings → Actions → General → Workflow permissions → select **Read and write permissions**. Without this the pipeline cannot commit results back to the repo.

---

## How to run locally

```bash
# 1. Clone the repo
git clone https://github.com/AhzamAhd/observatory-weather.git
cd observatory-weather

# 2. Create and activate virtual environment
py -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the full pipeline
python fetch_weather.py
python load_database.py
python score_quality.py
python visualize.py
```

---

## Triggering a manual update

**On GitHub:** Actions tab → Daily Observatory Weather Pipeline → Run workflow

**Locally:**
```bash
python fetch_weather.py
python load_database.py
python score_quality.py
python visualize.py
```

---

## Problems solved during build

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: requests` | Running Python outside the venv | Activated venv with `venv\Scripts\activate` |
| Git push denied (403) | Wrong GitHub account in credentials | Cleared Windows Credential Manager, re-authenticated |
| GitHub Actions deprecated actions | Using v3 of artifact actions | Upgraded all actions to v4 |
| `visualise.py` not found in Actions | File named `visualize.py` (z not s) | Fixed filename in workflow YAML |
| Git push permission denied (exit 128) | Actions lacked write permission | Added `permissions: contents: write` and enabled in repo settings |
| Duplicate rows in database | Pipeline ran multiple times during testing | `UNIQUE(observatory_id, timestamp_utc)` constraint handles this |

---

## What I learned

- How to design and call REST APIs with proper error handling in Python
- How to structure a relational database schema with foreign keys and constraints
- How to write SQL transformation logic using CASE WHEN and CREATE VIEW
- How to apply domain knowledge (astronomy physics) to engineer a meaningful metric
- How to build an automated pipeline with GitHub Actions using cron scheduling
- How to follow the medallion architecture (Bronze / Silver / Gold)
- How to debug GitHub Actions by reading step-by-step logs
- How to manage Git credentials and repository permissions

---

## CV description

**Automated Observational Quality Pipeline (Python · SQLite · GitHub Actions)**

- Developed an automated ETL pipeline to monitor atmospheric conditions for 5 global observatories via the Open-Meteo REST API, fetching cloud cover, humidity, wind speed, and temperature daily
- Designed a two-table relational schema in SQLite with foreign keys, parameterised queries, and deduplication constraints to store and version-control daily weather data points
- Engineered a physics-based SQL scoring algorithm weighted across three atmospheric variables to quantify telescope observation quality on a 0–100 scale
- Automated daily data ingestion, transformation, and chart generation using GitHub Actions cron scheduling, with results auto-committed back to the repository
- Applied the medallion architecture (Bronze / Silver / Gold) to separate raw ingestion, structured storage, and analytical output across three data layers

---

## Future improvements

- Add a Telegram or email alert when any observatory drops below a score of 40
- Expand to 20+ observatories globally
- Replace SQLite with PostgreSQL for multi-user access
- Add a 7-day forecast score using Open-Meteo's forecast endpoint
- Build a live Streamlit dashboard to visualise scores in the browser
- Add moon phase data — full moon reduces observation quality for faint objects

---

## Author

**Ahzam Ahmed**
Aspiring Data Engineer
[GitHub](https://github.com/AhzamAhd)

---

*Data sourced from [Open-Meteo](https://open-meteo.com) — free, open-source weather API. No API key required.*