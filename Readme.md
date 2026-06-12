# GOWC — Global Observatory Weather Tracker

### Real-time weather intelligence for astronomers worldwide

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b) ![Postgres](https://img.shields.io/badge/Database-Supabase%2FPostgres-3ecf8e) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Live-brightgreen)

**Live site → [gowcastroclimate.com](https://gowcastroclimate.com)**

---

## What is GOWC?

GOWC is a real-time weather and observing-conditions platform for **1,163 professional observatories** worldwide. It pulls live atmospheric data, scores each site for observing quality, models the physics that actually matters to telescopes (seeing, airmass, atmospheric extinction, precipitable water vapour), and presents it all through an interactive dashboard.

It's built for astronomers, researchers, and observatory operators who need to answer one question quickly: **where and when is the sky clearest tonight?**

---

## Features

| Page | What it does |
|---|---|
| **Live Weather Map** | Interactive world map with real-time observation-quality scores for every observatory, with satellite/street tiles, search, and marker clustering. |
| **Observing Windows** | Best time windows to observe tonight at any site, factoring weather, darkness and atmosphere. |
| **Object Visibility** | Which galaxies, nebulae and planets are visible tonight from a chosen observatory. |
| **Peak Observing Time** | The exact hour conditions peak at each site. |
| **Atmospheric Analysis** | Seeing quality, precipitable water vapour, jet-stream impact and turbulence. |
| **Historical Reliability** | Long-term reliability scores, trend direction and % of excellent nights per site. |
| **Site Comparison** | Compare up to 5 observatories side-by-side across all metrics. |
| **Semester Planning** | Best months and sites for target objects across an observing semester. |
| **Telescope Efficiency** | Efficiency ratings for optical, infrared and radio telescopes from live conditions. |
| **SNR Calculator** | Signal-to-noise predictions using a full CCD-noise model (shot, sky, dark, read, scintillation). |
| **Airmass Calculator** | Airmass curves over the night using the Pickering (2002) formula. |
| **7-Day Forecast** | Multi-day forecast scores per observatory. |
| **Comet / Asteroid / Satellite / Meteor / Eclipse trackers** | Live transient and event tracking with best-viewing-site recommendations. |
| **Observatory Detail** | Per-site deep dive: mini-map, nearby sites, and reliability history. |

---

## The science

GOWC uses real, citable astronomy physics rather than arbitrary scoring:

- **Atmospheric extinction** scales with site altitude using an exponential atmospheric-column model, calibrated to published mean extinction at ORM La Palma (V ≈ 0.12, R ≈ 0.09; King 1985) and ESO Paranal (V ≈ 0.11). Each observatory gets a realistic per-filter extinction coefficient based on its elevation.
- **Airmass** uses the **Pickering (2002)** formula, which is more accurate near the horizon than the plane-parallel `sec(z)` approximation.
- **Signal-to-noise** uses the standard CCD equation: `SNR = N_source / sqrt(N_source + N_sky + N_dark + N_read² + N_scint²)`, including a scintillation term and surface-brightness handling for extended objects.
- **Observation-quality score (0–100)** weights cloud cover, humidity (penalty above 85%) and wind speed (penalty above 15 m/s) by their real impact on telescope performance.

> **Disclaimer:** GOWC provides forecasts and physics-based estimates for *observation planning*. It is not a substitute for on-site measurements or official observatory conditions.

---

## Tech stack

| Layer | Tool |
|---|---|
| UI / dashboard | Streamlit |
| Database | Supabase (PostgreSQL) |
| Weather data | [Open-Meteo](https://open-meteo.com) API |
| Astronomy ephemerides | `ephem` / PyEphem |
| Visualisation | Plotly, Matplotlib |
| Backend compute | GitHub Actions (precompute) |
| Hosting | Render |

---

## Architecture

```
[Open-Meteo API] ──▶ fetch_weather.py ──▶ Supabase (Postgres)
                                              │
                          precompute.py ──────┤  (heavy calcs cached
                          (GitHub Actions)    │   to `precomputed` table)
                                              ▼
                                        dashboard.py (Streamlit)
                                              │
                                              ▼
                                    gowcastroclimate.com (Render)
```

Heavy calculations (reliability scores, eclipse best-sites, meteor showers, observing windows) are **precomputed** into a `precomputed` table so the live dashboard stays fast. Precompute runs on demand via the "Fetch Live Data" button and through GitHub Actions.

---

## Running locally

```bash
git clone https://github.com/AhzamAhd/observatory-weather.git
cd observatory-weather

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac / Linux

pip install -r requirements.txt
```

Set the following environment variables (Supabase credentials):

```
SUPABASE_DB_HOST
SUPABASE_DB_USER
SUPABASE_DB_PASSWORD
SUPABASE_URL
```

Then launch the dashboard:

```bash
streamlit run dashboard.py
```

---

## Data sources & credits

- Weather data — [Open-Meteo](https://open-meteo.com) (free, open-source, no API key)
- Ephemerides — [PyEphem](https://rhodesmill.org/pyephem/)
- Extinction coefficients — King (1985), ESO Paranal site monitoring, ORM La Palma
- Airmass — Pickering, K. A. (2002), *The Southern Limits of the Ancient Star Catalog*
- SFR/Hα methodology references — Kennicutt (1998)

---

## Author

**Ahzam Ahmed** · [GitHub](https://github.com/AhzamAhd)

Licensed under the MIT License.
