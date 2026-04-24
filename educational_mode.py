EDUCATIONAL_CONTENT = {

    # ── Weather metrics ───────────────────────────────────────────
    "cloud_cover": {
        "title": "Cloud Cover",
        "symbol": "%",
        "simple": "How much of the sky is covered by clouds.",
        "detailed": """
Cloud cover is measured as a percentage of the sky obscured by clouds.
For astronomical observation, clouds are the single biggest obstacle.
Even thin cirrus clouds scatter and absorb light, reducing the
brightness of faint objects and making precise measurements impossible.

- 0–10%: Clear sky. Excellent for all observation types.
- 10–30%: Mostly clear. Some thin cloud may affect faint objects.
- 30–60%: Partly cloudy. Marginal for serious work.
- 60–100%: Cloudy to overcast. Observation not recommended.

Professional observatories track cloud cover using all-sky cameras
that photograph the entire dome of the sky every few minutes.
        """,
        "fun_fact": "The Atacama Desert in Chile, home to some of the world's greatest observatories, has over 300 clear nights per year — one of the highest counts on Earth.",
        "formula": "Cloud Cover Score = 100 - (cloud_cover_pct × 0.50)",
        "weight": "50% of total observation score",
        "emoji": "☁️"
    },

    "humidity": {
        "title": "Humidity",
        "symbol": "%",
        "simple": "How much water vapour is in the air near the ground.",
        "detailed": """
Relative humidity measures how much water vapour the air holds
compared to its maximum capacity at that temperature.

For astronomy, humidity is critical for two reasons:
1. Above ~85%, moisture begins to condense on telescope mirrors
   and lenses, causing fogging that ruins optical performance.
2. High humidity increases atmospheric scattering of light,
   reducing the transparency of the sky.

- Below 50%: Ideal. Mirrors stay dry, sky is transparent.
- 50–70%: Acceptable for most observations.
- 70–85%: Marginal. Monitor closely, especially near dew point.
- Above 85%: Dangerous for optics. Close the dome.

Large professional telescopes have heated mirror edges to prevent
dew formation even in humid conditions.
        """,
        "fun_fact": "The Atacama Large Millimeter Array (ALMA) operates at 5,058m altitude partly because the air there contains almost no water vapour — essential for radio astronomy.",
        "formula": "Humidity Penalty = (humidity_pct - 85) × 2.0  (only above 85%)",
        "weight": "30% of total observation score",
        "emoji": "💧"
    },

    "wind_speed": {
        "title": "Wind Speed",
        "symbol": "m/s",
        "simple": "How fast the air is moving at the telescope site.",
        "detailed": """
Wind affects telescopes in two important ways:

1. Mechanical vibration: Strong wind physically shakes the telescope
   structure, causing images to blur. Even a 1mm movement at the
   mirror translates to significant image degradation.

2. Dome seeing: Wind creates turbulent airflow inside the dome,
   mixing air of different temperatures and degrading the image.

- Below 5 m/s: Calm. Excellent for all observation.
- 5–10 m/s: Light breeze. Minimal effect on most telescopes.
- 10–15 m/s: Moderate. Larger telescopes may show vibration.
- Above 15 m/s: Strong. Most observatories close the dome.
- Above 20 m/s: Dangerous. Risk of dome damage.

The largest telescopes (VLT, Keck) can operate in winds up to
about 18 m/s thanks to their massive, rigid structures.
        """,
        "fun_fact": "The Extremely Large Telescope (ELT) being built in Chile will have a 39-metre mirror — so large that even tiny vibrations from wind must be corrected 1,000 times per second.",
        "formula": "Wind Penalty = (wind_speed_ms - 15) × 2.0  (only above 15 m/s)",
        "weight": "20% of total observation score",
        "emoji": "💨"
    },

    # ── Atmospheric metrics ───────────────────────────────────────
    "seeing": {
        "title": "Atmospheric Seeing",
        "symbol": "arcseconds (\")",
        "simple": "How much the atmosphere blurs starlight. Lower is better.",
        "detailed": """
Atmospheric seeing describes how much the turbulent atmosphere
blurs the image of a star. Even on a perfectly clear night with
no clouds, temperature differences in the atmosphere cause
starlight to bend in random directions — this is why stars twinkle.

Seeing is measured in arcseconds. One arcsecond is 1/3600 of
a degree — an incredibly small angle. The smaller the seeing
value, the sharper the images.

- Below 0.5\": Exceptional. Rarely achieved anywhere on Earth.
- 0.5–1.0\": Excellent. World-class sites like Mauna Kea.
- 1.0–1.5\": Good. Suitable for most professional work.
- 1.5–2.5\": Average. Fine for bright objects and wide fields.
- Above 2.5\": Poor. Faint objects severely affected.

Space telescopes like Hubble have effectively 0\" seeing because
they operate above the atmosphere entirely.
        """,
        "fun_fact": "The best seeing on Earth has been measured at around 0.3 arcseconds at Dome C in Antarctica during winter — better than many space telescope resolutions.",
        "formula": "Seeing ≈ wind_factor × humidity_factor × altitude_factor × temperature_factor",
        "weight": "Not in main score — used for professional scheduling",
        "emoji": "👁️"
    },

    "pwv": {
        "title": "Precipitable Water Vapor (PWV)",
        "symbol": "mm",
        "simple": "Total water in the atmosphere above the telescope. Lower is better.",
        "detailed": """
Precipitable Water Vapor (PWV) measures the total amount of
water vapour in a column of atmosphere above the observatory,
expressed as the depth of liquid water it would form if
all condensed.

PWV is critical for infrared and radio astronomy because water
molecules absorb infrared and radio wavelengths, blocking the
signals astronomers want to detect. This is why infrared
telescopes are built at high, dry sites.

- Below 1mm: Exceptional. Essential for submillimetre astronomy.
- 1–2mm: Excellent. Good for near-infrared work.
- 2–5mm: Good. Suitable for most infrared observations.
- 5–10mm: Average. Some infrared windows remain usable.
- Above 10mm: Poor. Infrared and radio work severely limited.

ALMA requires PWV below 1mm to operate at its highest frequencies.
Mauna Kea was chosen for the James Clerk Maxwell Telescope
specifically because of its consistently low PWV.
        """,
        "fun_fact": "The South Pole has PWV values as low as 0.25mm in winter, making Antarctica one of the best places on Earth for terahertz and submillimetre astronomy.",
        "formula": "PWV ≈ 0.1 × actual_vapour_pressure × scale_height",
        "weight": "Not in main score — critical for IR/radio telescope scheduling",
        "emoji": "🌫️"
    },

    "jet_stream": {
        "title": "Jet Stream",
        "symbol": "m/s at 250hPa (~10km altitude)",
        "simple": "Fast winds high in the atmosphere that blur telescope images.",
        "detailed": """
The jet stream is a band of fast-moving air at about 10km
altitude (the tropopause). It flows around the Earth at
speeds of 30–100 m/s and causes the worst atmospheric seeing
when it passes directly over an observatory.

Unlike ground-level wind, the jet stream affects image quality
through turbulence in the upper atmosphere — mixing air layers
of different temperatures and densities.

- Below 20 m/s: Negligible impact on seeing.
- 20–40 m/s: Low impact. Seeing slightly degraded.
- 40–60 m/s: Moderate. Noticeably worse images.
- 60–80 m/s: High. Significant seeing degradation.
- Above 80 m/s: Severe. Professional work not viable.

Observatories like Mauna Kea and the Canary Islands are sometimes
positioned near the edges of the jet stream, which is why
seeing conditions there can change rapidly.
        """,
        "fun_fact": "Pilots use jet stream data to save fuel on transatlantic flights. The same data astronomers use to check seeing conditions helps planes fly faster when going east.",
        "formula": "Jet Impact = jet_stream_ms × (1 - latitude_factor × 0.3)",
        "weight": "Not in main score — used for professional seeing estimates",
        "emoji": "🌪️"
    },

    # ── Astronomical concepts ─────────────────────────────────────
    "moon_phase": {
        "title": "Moon Phase",
        "symbol": "% illumination",
        "simple": "How much of the Moon is lit up. Less is better for observing.",
        "detailed": """
The Moon is the astronomer's greatest enemy for faint object work.
Moonlight scatters off the atmosphere and floods the sky with
light, washing out dim galaxies, nebulae, and stars.

Moon phases complete a cycle of about 29.5 days:
- New Moon (0%): Darkest skies. Best for deep sky objects.
- Crescent (1–35%): Still relatively dark. Good for most work.
- Quarter (35–60%): Sky background noticeably brighter.
- Gibbous (60–85%): Significant light pollution from Moon.
- Full Moon (100%): Only bright objects and planets viable.

The Moon penalty in our scoring only applies when the Moon
is above the horizon AND significantly illuminated.
        """,
        "fun_fact": "The Moon moves across the sky at about 0.5 degrees per hour — roughly its own diameter. Astronomers track this carefully when planning long exposures.",
        "formula": "Moon Penalty = (moon_phase / 100) × 40 × (moon_altitude / 90)",
        "weight": "Applied to observing window score",
        "emoji": "🌙"
    },

    "astronomical_twilight": {
        "title": "Astronomical Twilight",
        "symbol": "Sun at -18° below horizon",
        "simple": "When the sky is truly dark enough for serious astronomy.",
        "detailed": """
Twilight comes in three stages as the Sun sets below the horizon:

1. Civil Twilight (0° to -6°): Still bright enough to read outside.
   Most stars not yet visible.

2. Nautical Twilight (-6° to -12°): Horizon still visible at sea.
   Brighter stars and planets appear.

3. Astronomical Twilight (-12° to -18°): Sky still has a slight
   glow on the horizon. Most stars visible but faint nebulae
   and galaxies are affected.

4. True Night (-18° and below): Sky is as dark as it gets.
   All objects can be observed at full depth.

We use astronomical twilight (-18°) to define the start and
end of the usable observing window in our calculations.
        """,
        "fun_fact": "In mid-summer at latitudes above 48.5°N (including much of the UK and northern Europe), the Sun never reaches -18° below the horizon, meaning astronomical night never truly arrives.",
        "formula": "Dark hours = time between dusk (-18°) and dawn (-18°)",
        "weight": "35% of peak observing time score",
        "emoji": "🌅"
    },

    "observation_score": {
        "title": "Observation Quality Score",
        "symbol": "0–100",
        "simple": "A single number summarising how good tonight is for telescope work.",
        "detailed": """
The Observation Quality Score combines three atmospheric
variables into a single 0–100 number, weighted by how much
each affects real telescope performance.

The formula:
Score = 100
      - (cloud_cover × 0.50)
      - (humidity penalty × 0.30 weight)
      - (wind penalty × 0.20 weight)

Interpretation:
- 80–100: Excellent. Open the dome. All observation types viable.
- 60–79: Good. Most science programmes can proceed.
- 40–59: Marginal. Bright targets only. Check conditions frequently.
- 0–39: Poor. Dome should remain closed.

This scoring system mirrors the decision-making process used
by real observatory operators when deciding whether to open.
        """,
        "fun_fact": "The world's most productive observatories aim for at least 70% of nights being usable. Paranal in Chile achieves about 87% — one of the highest rates on Earth.",
        "formula": "Score = 100 - (cloud×0.5) - (humidity penalty) - (wind penalty)",
        "weight": "Primary ranking metric",
        "emoji": "⭐"
    },

    # ── Telescope types ───────────────────────────────────────────
    "optical_telescope": {
        "title": "Optical Telescope",
        "symbol": "Visible light: 380–700nm",
        "simple": "A telescope that collects visible light — what humans can see.",
        "detailed": """
Optical telescopes collect and focus visible light using mirrors
(reflectors) or lenses (refractors). Most large professional
telescopes are reflectors because mirrors can be made much
larger than lenses without distortion.

Key parameters:
- Aperture: The diameter of the primary mirror or lens. Larger
  aperture collects more light and resolves finer detail.
- Focal length: Determines magnification and field of view.
- Focal ratio (f/number): Focal length divided by aperture.

For optical work, the most important conditions are:
- Low cloud cover (transparency)
- Good seeing (sharpness)
- Low moon illumination (sky darkness)
- Low humidity (mirror safety)
        """,
        "fun_fact": "The largest optical telescope on Earth is the Gran Telescopio Canarias on La Palma with an 10.4m mirror. The ELT under construction will have a 39.3m mirror.",
        "formula": "Resolving power (arcsec) = 116 / aperture_mm",
        "weight": "Uses all weather score components",
        "emoji": "🔭"
    },

    "radio_telescope": {
        "title": "Radio Telescope",
        "symbol": "Radio waves: 1mm–10m",
        "simple": "A telescope that detects radio waves from space instead of light.",
        "detailed": """
Radio telescopes detect radio waves emitted by cosmic objects —
from hydrogen gas in galaxies to supermassive black holes.
They look like giant satellite dishes and can operate through
clouds and even light rain.

Key advantages over optical:
- Can observe through clouds (radio waves penetrate most clouds)
- Can operate in daylight (the Sun doesn't drown out radio sources)
- Can detect objects invisible to optical telescopes

Key disadvantages:
- Much lower angular resolution (radio waves are longer than light)
- Severely affected by human-made radio interference
- High-frequency radio (millimetre) is blocked by water vapour

For radio work, the most important conditions are:
- Low Precipitable Water Vapor (PWV) — especially for mm-wave
- Low wind speed (dish vibration)
- No thunderstorms
        """,
        "fun_fact": "When the Event Horizon Telescope photographed the black hole in M87 in 2019, it linked radio telescopes on six continents to create an Earth-sized telescope.",
        "formula": "Resolution = 1.22 × wavelength / aperture (in same units)",
        "weight": "PWV is most critical metric for radio astronomy",
        "emoji": "📡"
    },

    "infrared_telescope": {
        "title": "Infrared Telescope",
        "symbol": "Infrared: 700nm–1mm",
        "simple": "A telescope that sees heat radiation — invisible to human eyes.",
        "detailed": """
Infrared telescopes detect heat radiation from cosmic objects.
Infrared is emitted by cool objects that don't shine in visible
light — dust clouds, cool stars, and the very early universe.

The James Webb Space Telescope is primarily an infrared telescope,
which is why it orbits far from Earth where the background
infrared emission is cold and stable.

Ground-based infrared telescopes face a critical challenge:
the Earth's own atmosphere emits infrared radiation, creating
a warm glowing background. Water vapour is the biggest culprit.

This is why infrared observatories are built at:
- High altitude (above most water vapour)
- Dry climates (low PWV)
- Cold temperatures (less thermal emission)

Mauna Kea is ideal for infrared because it sits above 40%
of Earth's atmosphere and most of its water vapour.
        """,
        "fun_fact": "The James Webb Space Telescope must be kept colder than -233°C (40K) to prevent its own heat from drowning out the faint infrared signals it detects.",
        "formula": "Atmospheric transmission improves exponentially with altitude above water vapour layer",
        "weight": "PWV is the critical metric. Below 2mm essential.",
        "emoji": "🌡️"
    },

    # ── Key sites ─────────────────────────────────────────────────
    "mauna_kea": {
        "title": "Mauna Kea, Hawaii",
        "symbol": "4,205m · 19.8°N",
        "simple": "One of the world's top observatory sites, on a Hawaiian volcano.",
        "detailed": """
Mauna Kea is a dormant volcano on the Big Island of Hawaii.
At 4,205m, it sits above most of the Pacific's cloud layer
and water vapour, giving it some of the best conditions on Earth.

Why Mauna Kea is exceptional:
- Above the inversion layer (the persistent cloud deck)
- Extremely low PWV — critical for infrared work
- Seeing of 0.4–0.6 arcseconds on the best nights
- Over 300 clear nights per year
- Dark skies far from major city light pollution

Telescopes at Mauna Kea include:
- W.M. Keck Observatory (twin 10m mirrors)
- Subaru Telescope (8.2m)
- NASA Infrared Telescope Facility (IRTF)
- James Clerk Maxwell Telescope (radio)
        """,
        "fun_fact": "Mauna Kea is the tallest mountain on Earth when measured from its base on the ocean floor — taller than Everest by over a kilometre.",
        "formula": "Altitude advantage: PWV halves approximately every 2km of elevation",
        "weight": "Reference site for world-class seeing",
        "emoji": "🌋"
    },

    "paranal": {
        "title": "Paranal Observatory, Chile",
        "symbol": "2,635m · 24.6°S",
        "simple": "Home of the Very Large Telescope — one of the most powerful on Earth.",
        "detailed": """
Cerro Paranal is a 2,635m mountain in the Atacama Desert,
the driest non-polar desert on Earth. It is operated by the
European Southern Observatory (ESO) and hosts the Very Large
Telescope (VLT) — four 8.2m telescopes that can combine to
act as a single giant instrument.

Why Paranal is exceptional:
- Atacama Desert receives less than 10mm of rainfall per year
- Over 340 clear nights annually
- Very low humidity — mirrors rarely threatened by dew
- Exceptional seeing: median ~0.65 arcseconds
- Southern hemisphere location — unique sky access

Paranal hosts:
- VLT (four 8.2m telescopes + four 1.8m auxiliary)
- VLTI (interferometric combination of VLT)
- VST (survey telescope)
- VISTA (infrared survey telescope)
        """,
        "fun_fact": "The Atacama Desert is so dry that NASA uses it to test Mars rovers — the conditions are the closest to Martian surface conditions found on Earth.",
        "formula": "Site quality index: 340 clear nights × 0.65\" median seeing = world-class",
        "weight": "Reference site for southern hemisphere excellence",
        "emoji": "🏜️"
    },
}

def get_concept(key):
    return EDUCATIONAL_CONTENT.get(key)

def get_all_concepts():
    return EDUCATIONAL_CONTENT

def get_concepts_by_category():
    categories = {
        "Weather Metrics": [
            "cloud_cover", "humidity",
            "wind_speed", "observation_score"
        ],
        "Atmospheric Science": [
            "seeing", "pwv",
            "jet_stream", "astronomical_twilight"
        ],
        "Moon & Timing": [
            "moon_phase", "astronomical_twilight"
        ],
        "Telescope Types": [
            "optical_telescope", "radio_telescope",
            "infrared_telescope"
        ],
        "Famous Sites": [
            "mauna_kea", "paranal"
        ]
    }
    return categories
    