# GOWC — Tab Guide & Methodology

A complete reference for every page in the Global Observatory Weather Tracker:
what it does, and the maths/physics behind it. All formulas below reflect the
actual implementation in the codebase.

> **Disclaimer:** GOWC provides forecasts and physics-based *estimates* for
> observation planning. It is not a substitute for on-site measurements or
> official observatory conditions.

---

## Core formulas (used across many tabs)

| Concept | Formula | Module |
|---|---|---|
| Observing-quality index | `clarity × dryness × wind × seeing × jet × precip_gate` (multiplicative) | `atmospheric.py` |
| Airmass | `X = 1 / sin(h + 244/(165 + 47·h^1.1))` — Pickering (2002) | `airmass_calculator.py` |
| Atmospheric extinction | `T = 10^(−k·X/2.5)`, with `k` scaled by site altitude | `airmass_calculator.py` |
| Seeing (Fried) | `r₀ = (0.423·k²·X·∫Cₙ²dh)^(−3/5)`, `seeing = 0.98·λ/r₀` | `atmospheric.py` |
| PWV (Magnus) | `pwv = 0.1·(RH/100·svp)·2·exp(−alt/8000)` | `atmospheric.py` |
| SNR (CCD eq.) | `SNR = N⋆ / √(N⋆ + N_sky + N_dark + N_read² + N_scint²)` | `snr_calculator.py` |
| Astronomical darkness | Sun altitude `< −18°` | `ephem` |

**Observing-quality index (the headline 0–100 score).** Each factor is a
0–1 fraction; they multiply, so any single show-stopper (thick cloud, rain,
terrible seeing) correctly tanks the whole night — as in real observing.
This is the model used by ClearDarkSky / Meteoblue astronomy indices.
```
clarity     = (1 − cloud)^1.5         # non-linear: first cloud hurts most
dryness     = 1 → 0.5 as RH 70→100%   # condensation risk
wind_stab   = 1 → 0.2 as wind 8→33 m/s
seeing_fac  = 1 at ≤0.7", → 0.25 by ~3"   (Fried-based seeing)
jet_fac     = 1.0 (Negligible) … 0.5 (Severe)
precip_gate = 1.0 if dry, else 0.05   # any rain ⇒ dome closed
score       = clarity·dryness·wind_stab·seeing_fac·jet_fac·precip_gate × 100
```
A simpler **weather-only** score (`100 − cloud·0.5 − humidity/wind penalties`)
is still computed in SQL and kept as `weather_score` for reference, but the
headline `observation_score` is the multiplicative index above.

**Calibration anchors** (validated against published data):
- Extinction: La Palma ORM `k(V)≈0.12`, `k(R)≈0.09` (King 1985); Paranal `k(V)≈0.11`.
- Seeing: Mauna Kea ≈0.5″, Paranal ≈0.8″, La Palma ≈0.9″ (published medians).

---

## Overview

### 🏠 Home
**Does:** Landing page — banner, live stats (sites, excellent/good counts, average
score, best site tonight), feature grid, and a getting-started guide.
**Maths:** Aggregation only — counts and the mean of observation scores.

### 🗺️ Live Weather Map
**Does:** Interactive world map; every observatory coloured by its observing-quality
score. Search, marker clustering, satellite/street tiles.
**Maths:** The **Observing-Quality Index (0–100)** — the multiplicative blend of
clarity, dryness, wind, seeing, jet stream and a precipitation gate (see core formulas).
**Physics:** Clouds block optical light (non-linear — even light cloud bites);
high humidity risks condensation; strong wind causes vibration/tracking errors; poor
seeing blurs images; any precipitation closes the dome. A single bad factor tanks the
score, which is why most sites most of the time score modestly — that is realistic.

### 📖 About & Methodology
**Does:** In-app documentation of the physics with formulas and citations.

---

## Planning

### 🌙 Observing Windows (includes Peak Observing Time)
**Does:** Tonight's dark-time windows per site (ranked), plus the single peak observing
hour and an hourly breakdown chart.
**Maths:**
- Dark window from astronomical twilight (Sun at **−18°**), via `ephem`.
- **Moon penalty**, applied only when the Moon is above the horizon during the window:
  ```
  >85% illum → −40  |  >60% → −25  |  >35% → −15  |  >10% → −5
  final_score = weather_score − moon_penalty
  ```
- **Hourly combined score** (peak section, no target):
  ```
  combined = weather·0.35 + darkness·0.25 + moon·0.20 + object·0.20
  ```
- **SNR-driven peak (when a target + magnitude + band are chosen):** each dark hour
  gets a real SNR — object altitude → airmass → band extinction → moon sky brightness
  → CCD equation — and the **peak hour is the hour of maximum SNR**, i.e. genuine
  detectability rather than just "highest in the sky".
**Physics:** Astronomical twilight (−18°) marks a fully dark sky; a bright Moon above
the horizon raises sky background and washes out faint targets; detectability also
depends on the object's brightness, the filter bandwidth and airmass.

### 🔭 Object Visibility
**Does:** For a chosen object, ranks observatories by how well they can see it right now.
**Maths:** `ephem` gives the object's **altitude/azimuth** from each site; that altitude
is converted to **airmass** (Pickering 2002) and **V-band extinction** scaled by site
altitude. Sites are ranked by `weather·0.6 + transmission·100·0.4`, where
`transmission = 10^(−extinction/2.5)`.
**Physics:** An object must be above the horizon (ideally high). Higher altitude → lower
airmass → less extinction → more light reaches the telescope. Two sites at the same
altitude no longer tie — a high, dry site transmits more than a low one.

### 📝 Observing Proposal Planner
**Does:** Assembles the computable core of a professional observing proposal (modelled on
the La Palma PHY430 11-section brief): target list, observing time, moon phase, preferred
date, SNR-solved exposure times, and an exportable draft. Includes a best-months calendar.
**Maths:**
- **Exposure per target (§9)** — solved by bisection to reach a chosen SNR via the full
  CCD equation in the selected band, with airmass extinction and moon sky brightness.
- **Observing time (§3)** — Σ exposures × 1.4 (≈40% slew/readout/acquisition overhead).
- **Preferred time (§5)** — best dark hour tonight from the peak-time engine.
- **Target list (§6)** — RA/Dec (J2000), V-mag, B−V (where catalogued), altitude, airmass.
**Physics:** Same airmass/extinction/SNR physics as the SNR Calculator, organised around
the structure of a real telescope-time proposal. Sections 1, 2, 8, 10, 11 are user input.

### 📅 7-Day Forecast
**Does:** 7-day predicted observation-quality scores per observatory.
**Maths:** The observation-score formula applied to Open-Meteo *forecast* data.

### 📐 Airmass Calculator
**Does:** Plots airmass vs time for an object at a site over the night.
**Maths:** Pickering (2002) airmass (see core formulas).
**Physics:** Airmass = how much atmosphere light traverses (1.0 at zenith). Lower is
better; professional observations usually stay below airmass ≈ 2.

---

## Analysis

### 🌫️ Atmospheric Analysis
**Does:** Seeing, PWV and jet-stream impact for every site.
**Maths:**
- **Seeing** — Hufnagel–Valley-style `∫Cₙ²dh` → Fried parameter `r₀` → `seeing = 0.98·λ/r₀`.
- **PWV** — Magnus saturation vapour pressure scaled by altitude.
- **Jet stream** — impact scaled by latitude (strongest at 30–60°).
**Physics:** Seeing is turbulence-induced blurring (the key sharpness metric); PWV is
water vapour that absorbs infrared/sub-mm; a jet stream overhead means turbulence aloft
and poor seeing.

### 📊 Historical Reliability
**Does:** Long-term reliability grade (A+ to D) per site from accumulated daily data.
**Maths:** Each day's score is the same genuine observing-quality index (computed from
that day's averaged conditions), then:
```
reliability = avg_score·0.50 + consistency·0.25 + %excellent·0.25
consistency = 100 − 2·std(daily_scores)
trend       = mean(second half) − mean(first half)
```
**Physics:** Statistics on the historical observing-quality distribution.

### 🔬 Site Comparison
**Does:** Compare 2–5 observatories side-by-side across all metrics.
**Maths:** Pulls each site's current, historical and atmospheric values; no new formula.

### 🏆 Telescope Efficiency
**Does:** A single 0–100 "usable hours tonight" score per telescope type.
**Maths:**
```
score        = weather·w₁ + dark·w₂ + moon·w₃ + seeing·w₄ + pwv·w₅ + jet·w₆
usable_hours = dark_hours · (score / 100)
```
Weights vary by telescope type — infrared/radio weight **PWV** higher; optical weights
**seeing** higher.
**Physics:** Combines every limiting factor into the number a scheduler cares about:
productive observing hours.

### 📡 SNR Calculator
**Does:** Predicts signal-to-noise for an object at each site, with a filter selector
(V / B / R / I / Hα / OIII).
**Maths:** The CCD equation (see core formulas). Source photons depend on magnitude and
the filter's **bandwidth**; extinction uses the per-altitude `k`.
**Physics:** How detectable a target is. Bright objects, large apertures, dark skies, low
airmass and wide filters all raise SNR. Narrowband filters (Hα ~3 nm) collect roughly
40× fewer photons than broadband, isolating emission lines at the cost of signal.

### 🔬 Observatory Detail
**Does:** Deep-dive on one site — mini-map, nearby sites, reliability history, all live
metrics.
**Maths:** Re-runs the above calculations for the single selected site.

---

## Sky Events

### ☄️ Comet Tracker / 🪨 Asteroid Tracker / 🛸 Satellite Passes / 🌠 Meteor Showers / 🌑 Eclipses & Transits
**Does:** Live transient/event tracking plus which observatories have the best view.
**Maths / physics:**
- **Comets / Asteroids** — orbital data (NASA NeoWs for asteroids): magnitude, miss
  distance (in lunar distances), size, velocity, threat assessment.
- **Satellites** — TLE orbital propagation to predict ISS passes: rise/set, brightness,
  direction, duration.
- **Meteor showers** — ZHR (zenithal hourly rate), Moon-phase-at-peak penalty, radiant
  altitude, observing score.
- **Eclipses & transits** — ephemeris dates and, per event, the best observatories by
  weather and visibility geometry.

---

## More

### 🌌 Live Sky Chart
**Does:** Real-time planetarium view for a site — stars, planets, Moon, your target.
**Maths:** `ephem` altitude/azimuth positions projected onto a sky dome.

### 🎓 Learn Astronomy
**Does:** Plain-language explanations of every metric. Educational; no computation.

### 🔔 Alert Subscriptions
**Does:** Email alerts when a site crosses a chosen score threshold. Checked daily by a
GitHub Actions job.

---

## References

- Pickering, K. A. (2002), *The Southern Limits of the Ancient Star Catalog* — airmass.
- King, D. L. (1985), *Atmospheric Extinction at the Roque de los Muchachos Observatory* — extinction.
- ESO Paranal site monitoring — extinction/seeing cross-check.
- Kennicutt (1998) — Hα → star-formation-rate methodology.
- Weather data: [Open-Meteo](https://open-meteo.com). Ephemerides: [PyEphem](https://rhodesmill.org/pyephem/).
