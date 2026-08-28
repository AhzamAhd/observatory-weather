# GOWC — Global Observatory Weather Tracker

### Real-time weather intelligence for astronomers worldwide

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b) ![Postgres](https://img.shields.io/badge/Database-Supabase%2FPostgres-3ecf8e) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Live-brightgreen)

**Live site → [gowcastroclimate.com](https://gowcastroclimate.com)**

---

## What is GOWC?

GOWC is a real-time weather and observing-conditions platform for **~2,600 professional observatories** worldwide. It pulls live atmospheric data, scores each site for observing quality, models the physics that actually matters to telescopes (seeing, airmass, atmospheric extinction, precipitable water vapour, sky brightness, signal-to-noise), and presents it all through an interactive dashboard. Its photometric SNR calculator is **validated against the ING SIGNAL exposure-time calculator** to within a few percent on two independent instruments.

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
| **Plan an Observation** | Guided 8-step wizard: target → site → night → visibility → best window → conditions → exposure/SNR → exportable observing plan. |
| **Transient Follow-Up** | Active neutron-star X-ray binaries with live MAXI outburst alerts and observability. |
| **Telescope Efficiency** | Efficiency ratings for optical, infrared and radio telescopes from live conditions. |
| **SNR Calculator** | Signal-to-noise predictions using a full CCD-noise model (shot, sky, dark, read, scintillation). |
| **Airmass Calculator** | Airmass curves over the night using the Pickering (2002) formula. |
| **7-Day Forecast** | Multi-day forecast scores per observatory. |
| **Comet / Asteroid / Satellite / Meteor / Eclipse trackers** | Live transient and event tracking with best-viewing-site recommendations. |
| **Observatory Detail** | Per-site deep dive: mini-map, nearby sites, and reliability history. |

---

## The science

GOWC uses real, citable astronomy physics rather than arbitrary scoring. Every model comes from the published literature, and the calculations are validated where ground truth exists.

- **Seeing** uses the **Tatarski C<sub>n</sub><sup>2</sup> formulation** driven by a real vertical temperature gradient from the 850/500 hPa pressure levels (θ → C<sub>T</sub>² → C<sub>n</sub>² → Fried parameter r₀ → θ = 0.98λ/r₀), combined in quadrature with a ground/boundary-layer term. Refs: Tatarski (1971), Basu & Holtslag (2021), Fried (1966).
- **Airmass** uses the **Pickering (2002)** interpolative formula, more accurate near the horizon than plane-parallel `sec(z)`. Validated against the Kasten & Young (1989) tables to **< 0.34 %**.
- **Atmospheric extinction** follows the Bouguer law with primary and secondary (colour-dependent) coefficients, `k = k₁ + k₂(B−V)`, anchored to published La Palma / Paranal values (King 1985). Matches published site coefficients to **~0.01 mag/airmass**.
- **Precipitable water vapour** uses Open-Meteo's model-computed total-column water vapour, scaled to each site's altitude (`PWV(h) = PWV(0)·e^(−h/2000)`). Matches published site medians to **~30 %**.
- **Sky brightness** uses the **Krisciunas & Schaefer (1991)** moonlight model, folding in lunar phase, the Moon's and target's airmasses, and — the dominant term — the Moon–target angular separation.
- **Signal-to-noise** uses the standard CCD equation `SNR = N_source / √(N_source + N_sky + N_dark + N_read² + σ_scint²)` with the **Osborn et al. (2015)** scintillation term, per-band Vega zero-points (Bessell 1998), and a small catalogue of **real instruments** (INT/WFC, WHT/ACAM, VLT/FORS2, Keck/LRIS, Gemini/GMOS, pt5m). **Validated against the ING SIGNAL ETC** on two instruments (WHT/ACAM ~1 %, INT/WFC ~3 %). Reports magnitude uncertainty σ_m = 1.0857/SNR.
- **Observation-quality score (0–100)** is a *multiplicative* index of clarity, dryness, wind, seeing, jet-stream and a precipitation gate — a night is only as good as its worst limiting factor.

> **Scope & disclaimer:** GOWC implements the *forward (predictive)* half of the photometric pipeline (target → expected counts and SNR); it does not perform data reduction. It provides forecasts and physics-based estimates for *observation planning*, not a substitute for on-site measurements or official observatory conditions. Absolute seeing is reported uncalibrated and is indicative; relative rankings are reliable.

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

- Weather data — [Open-Meteo](https://open-meteo.com) (surface + 850/500/250 hPa pressure levels, total-column PWV; free, no API key)
- Observatory list — IAU Minor Planet Center observatory codes, plus flagship research facilities added manually
- Ephemerides — [PyEphem](https://rhodesmill.org/pyephem/)
- Seeing — Tatarski (1971); Basu & Holtslag (2021, arXiv:2110.03439); Fried (1966)
- Airmass — Pickering (2002); Kasten & Young (1989)
- Extinction — King (1985); ESO Paranal / ORM La Palma site monitoring
- Sky brightness — Krisciunas & Schaefer (1991)
- SNR / scintillation — Osborn et al. (2015); Kornilov et al. (2012); Young (1967); zero-points Bessell, Castelli & Plez (1998)
- SNR validation — ING SIGNAL exposure-time calculator (`astro.ing.iac.es/signal/`)
- Instrument constants — INT/WFC, WHT/ACAM, VLT/FORS2, Keck/LRIS, Gemini/GMOS, pt5m ETCs

---

## Author

**Ahzam Ahmed** · [GitHub](https://github.com/AhzamAhd)

Licensed under the MIT License.
