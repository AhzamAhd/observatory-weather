"""
Curated, factual description of GOWC — the grounding for the assistant's
"help" lane. The LLM may ONLY answer GOWC how-does-it-work questions using the
facts in GOWC_FACTS below; it must not invent features, pages, or numbers that
aren't here. Keep this in sync with the app when features change.
"""

GOWC_FACTS = """
GOWC (Global Observatory Weather Tracker) is a web app that reports real-time
observing conditions for 1,163+ professional observatories worldwide and helps
astronomers plan observations. Weather data comes from Open-Meteo. It is built
by Ahzam Ahmed.

## The headline observing-quality score (0-100)
Each observatory's score is a MULTIPLICATIVE observing-quality index, not a
simple average. It blends the factors that actually limit ground-based
observing: cloud clarity, dryness (humidity), wind, seeing, jet stream, and
precipitation. Because it's multiplicative, any single show-stopper (thick
cloud, rain, terrible seeing) drags the whole score down — a night is only as
good as its worst limiting factor. Condition bands: Excellent / Good /
Marginal / Poor.

## Key metrics explained
- Airmass: how much atmosphere you look through toward a target. 1.0 is
  straight up (best); it rises as the target gets lower. Below ~2 is good,
  above ~3 is poor. GOWC uses the Pickering (2002) airmass formula.
- Seeing (arcseconds): atmospheric blurring, from real Fried-parameter physics
  (r0 -> 0.98 x wavelength / r0), calibrated to published site values
  (Mauna Kea ~0.5", Paranal ~0.8", La Palma ~0.9"). Lower is sharper.
- Atmospheric extinction: how much the air dims starlight; scales with airmass
  and site altitude (higher, drier sites lose less light).
- Astronomical night: when the Sun is more than 18 degrees below the horizon —
  true darkness for deep-sky observing.
- SNR (signal-to-noise ratio): how cleanly a target can be measured given
  aperture, exposure, sky brightness and conditions.

## Pages and what they do
Navigation is a single dropdown, grouped:
- Overview: **Home** (summary + best site tonight); **Live Weather Map**
  (interactive world map of all observatories coloured by conditions).
- Planning: **Observing Windows** (when conditions are good at a site);
  **Object Visibility** (is an object up, airmass over the night);
  **Observing Proposal Planner** (build a full observing proposal).
- Analysis: **Atmospheric Analysis** (seeing, extinction, jet stream);
  **Historical Reliability** (long-term reliability, % of excellent nights);
  **Site Comparison** (compare observatories side by side);
  **Telescope Efficiency**; **SNR Calculator**; **Observatory Detail**
  (one site in depth); **Transient Follow-Up** (active X-ray-binary targets
  and live MAXI outburst alerts, with observability); **Observing Assistant**
  (this chatbot).
- Sky Events: **Sky Events** (meteor showers, eclipses, etc.).
- More: **Learn Astronomy**; **Alert Subscriptions** (email alerts when a site
  hits good conditions); **Observatory Reviews**; **Feedback & Suggestions**.

## Accounts and saving
Users can register/log in (top-right). Logged-in users can save observatories
and log observation sessions ("My Saves"), and save Live-Map searches.

## Transient Follow-Up
Lets a researcher pick a target class and see active targets/alerts plus GOWC's
observability layer. Neutron-star and black-hole X-ray binaries are live, fed
by a curated catalogue plus live outburst alerts from the MAXI/RIKEN monitor.
Other classes (supernovae, GRBs, kilonovae, etc.) are listed as "coming soon".

## Data & honesty
Forecasts are estimates for planning, not official observatory conditions.
Weather data is from Open-Meteo. The observing assistant computes observability
with a deterministic engine and never invents numbers.
"""
