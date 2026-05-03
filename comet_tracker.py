import requests
import ephem
import math
from datetime import datetime


# ── Comet type descriptions ───────────────────────────────────────
def comet_type_info(comet_type):
    types = {
        "Short-period":  "Orbital period under 200 years. Returns predictably.",
        "Long-period":   "Orbital period over 200 years. Often first-time visitors from the Oort Cloud.",
        "Centaur":       "Between Jupiter and Neptune. Unstable icy body that can become a comet.",
        "Interstellar":  "From outside our solar system entirely. Only 3 confirmed ever detected.",
        "MPC Listed":    "Currently listed by Minor Planet Center as observable.",
        "Sungrazer":     "Passes extremely close to the Sun. Often spectacular but frequently disintegrate.",
    }
    return types.get(comet_type, "Unknown type")


# ── Magnitude to visibility ───────────────────────────────────────
def magnitude_to_visibility(magnitude):
    if magnitude is None:
        return "Unknown"
    if magnitude < 0:    return "Extremely bright — visible in daylight"
    elif magnitude < 2:  return "Very bright — easy naked eye"
    elif magnitude < 4:  return "Bright — naked eye"
    elif magnitude < 6:  return "Naked eye in dark sky"
    elif magnitude < 8:  return "Binoculars needed"
    elif magnitude < 10: return "Small telescope"
    elif magnitude < 12: return "Medium telescope"
    elif magnitude < 15: return "Large telescope"
    else:                return "Professional telescope only"


# ── Position calculator ───────────────────────────────────────────
def calculate_comet_position(lat, lon, ra_deg, dec_deg):
    """
    Calculate altitude/azimuth of a comet given
    its RA/Dec coordinates.
    """
    if ra_deg is None or dec_deg is None:
        return None

    observer          = ephem.Observer()
    observer.lat      = str(lat)
    observer.long     = str(lon)
    observer.date     = datetime.utcnow().strftime(
        "%Y/%m/%d %H:%M:%S")
    observer.pressure = 0

    body      = ephem.FixedBody()
    body._ra  = ephem.degrees(str(ra_deg))
    body._dec = ephem.degrees(str(dec_deg))
    body.compute(observer)

    alt = math.degrees(float(body.alt))
    az  = math.degrees(float(body.az))

    try:
        observer.horizon = "0"
        rise     = observer.next_rising(body)
        sett     = observer.next_setting(body)
        rise_str = ephem.Date(
            rise).datetime().strftime("%H:%M UTC")
        set_str  = ephem.Date(
            sett).datetime().strftime("%H:%M UTC")
    except Exception:
        rise_str = "Circumpolar"
        set_str  = "Circumpolar"

    return {
        "altitude":  round(alt, 1),
        "azimuth":   round(az, 1),
        "visible":   alt >= 10,
        "rise_time": rise_str,
        "set_time":  set_str
    }


# ── Visibility from location ──────────────────────────────────────
def get_comet_visibility(comet, lat, lon):
    """
    Calculate visibility of a comet from given location.
    Returns None if no position data available.
    """
    if comet.get("ra_deg") is None:
        return None

    return calculate_comet_position(
        lat, lon,
        comet["ra_deg"],
        comet["dec_deg"]
    )


# ── Current comet catalogue ───────────────────────────────────────
def get_current_comets():
    """
    Currently notable comets — May 2026.
    Curated list with real current data.
    Positions are approximate for visibility calculations.
    """
    return [
        {
            "name":           "C/2025 R3 (PanSTARRS)",
            "designation":    "C/2025 R3",
            "type":           "Long-period",
            "period_yr":      None,
            "discovery_year": 2025,
            "discoverer":     "PanSTARRS survey",
            "magnitude":      4.5,
            "ra_deg":         340.0,
            "dec_deg":        -25.0,
            "notes":          (
                "Brightest comet of 2026 — peaked at "
                "magnitude 1.5 on April 26. Now fading "
                "but still visible in binoculars from "
                "Southern Hemisphere under dark skies."
            ),
            "perihelion":     "2026-04-19",
            "status":         "🟡 Fading — binoculars needed",
            "interesting":    True
        },
        {
            "name":           "10P/Tempel 2",
            "designation":    "10P",
            "type":           "Short-period",
            "period_yr":      5.0,
            "discovery_year": 1873,
            "discoverer":     "Wilhelm Tempel",
            "magnitude":      7.0,
            "ra_deg":         310.0,
            "dec_deg":        -15.0,
            "notes":          (
                "Approaching perihelion August 2, 2026. "
                "Could reach magnitude 6.8 at closest "
                "approach to Earth on August 3. "
                "Binoculars target this summer."
            ),
            "perihelion":     "2026-08-02",
            "status":         "🟢 Brightening — watch this summer",
            "interesting":    True
        },
        {
            "name":           "3I/ATLAS",
            "designation":    "3I",
            "type":           "Interstellar",
            "period_yr":      None,
            "discovery_year": 2025,
            "discoverer":     "ATLAS survey",
            "magnitude":      14.0,
            "ra_deg":         95.0,
            "dec_deg":        -20.0,
            "notes":          (
                "Third confirmed interstellar object ever "
                "detected — after 1I/Oumuamua and "
                "2I/Borisov. Passed closest to the Sun "
                "October 29, 2025. Now fading rapidly "
                "as it leaves the solar system forever."
            ),
            "perihelion":     "2025-10-29",
            "status":         "🔴 Fading — leaving solar system",
            "interesting":    True
        },
        {
            "name":           "29P/Schwassmann-Wachmann",
            "designation":    "29P",
            "type":           "Centaur",
            "period_yr":      14.9,
            "discovery_year": 1927,
            "discoverer":     "Schwassmann & Wachmann",
            "magnitude":      11.5,
            "ra_deg":         130.0,
            "dec_deg":        20.0,
            "notes":          (
                "Volcanic comet — cryovolcanic outbursts "
                "can brighten it by 4-5 magnitudes "
                "unpredictably. Always worth monitoring. "
                "Not due at perihelion until 2039."
            ),
            "perihelion":     "2039-03-01",
            "status":         "⚪ Active — watch for outbursts",
            "interesting":    True
        },
        {
            "name":           "67P/Churyumov-Gerasimenko",
            "designation":    "67P",
            "type":           "Short-period",
            "period_yr":      6.4,
            "discovery_year": 1969,
            "discoverer":     "Klim Churyumov",
            "magnitude":      18.0,
            "ra_deg":         120.0,
            "dec_deg":        15.0,
            "notes":          (
                "ESA Rosetta spacecraft orbited this "
                "comet 2014-2016 and Philae lander "
                "touched down on the surface — first "
                "ever comet landing. Famous rubber duck "
                "shape."
            ),
            "perihelion":     "2025-11-02",
            "status":         "🔴 Faint — large telescope only",
            "interesting":    True
        },
        {
            "name":           "2P/Encke",
            "designation":    "2P",
            "type":           "Short-period",
            "period_yr":      3.3,
            "discovery_year": 1786,
            "discoverer":     "Pierre Mechain",
            "magnitude":      15.0,
            "ra_deg":         90.0,
            "dec_deg":        10.0,
            "notes":          (
                "Shortest orbital period of any known "
                "comet at just 3.3 years. Has completed "
                "more observed returns than any other "
                "comet. Next perihelion August 9, 2026."
            ),
            "perihelion":     "2026-08-09",
            "status":         "🔴 Faint — approaching perihelion",
            "interesting":    True
        },
        {
            "name":           "1P/Halley",
            "designation":    "1P",
            "type":           "Short-period",
            "period_yr":      75.3,
            "discovery_year": -239,
            "discoverer":     "Ancient records",
            "magnitude":      28.0,
            "ra_deg":         None,
            "dec_deg":        None,
            "notes":          (
                "Most famous comet in history. Currently "
                "near aphelion beyond Neptune — completely "
                "unobservable. Will not return until "
                "July 28, 2061. Last seen in 1986."
            ),
            "perihelion":     "2061-07-28",
            "status":         "⚪ Near aphelion — unobservable",
            "interesting":    True
        },
        {
            "name":           "81P/Wild 2",
            "designation":    "81P",
            "type":           "Short-period",
            "period_yr":      6.4,
            "discovery_year": 1978,
            "discoverer":     "Paul Wild",
            "magnitude":      16.0,
            "ra_deg":         200.0,
            "dec_deg":        -10.0,
            "notes":          (
                "NASA Stardust spacecraft flew through "
                "the coma and collected dust samples "
                "in 2004 — returned to Earth 2006. "
                "Next perihelion May 2028."
            ),
            "perihelion":     "2028-05-21",
            "status":         "🔴 Faint — large telescope only",
            "interesting":    True
        },
        {
            "name":           "9P/Tempel 1",
            "designation":    "9P",
            "type":           "Short-period",
            "period_yr":      5.5,
            "discovery_year": 1867,
            "discoverer":     "Ernst Tempel",
            "magnitude":      17.0,
            "ra_deg":         150.0,
            "dec_deg":        5.0,
            "notes":          (
                "NASA Deep Impact spacecraft fired a "
                "370kg copper impactor into this comet "
                "in 2005, creating a crater and releasing "
                "material for analysis. Next perihelion "
                "April 2027."
            ),
            "perihelion":     "2027-04-01",
            "status":         "🔴 Faint — large telescope only",
            "interesting":    True
        },
        {
            "name":           "103P/Hartley 2",
            "designation":    "103P",
            "type":           "Short-period",
            "period_yr":      6.5,
            "discovery_year": 1986,
            "discoverer":     "Malcolm Hartley",
            "magnitude":      16.0,
            "ra_deg":         240.0,
            "dec_deg":        30.0,
            "notes":          (
                "EPOXI mission flew past at just 700km "
                "in November 2010. Images revealed a "
                "peanut-shaped nucleus with active jets. "
                "Next perihelion October 2029."
            ),
            "perihelion":     "2029-10-01",
            "status":         "🔴 Faint — large telescope only",
            "interesting":    True
        },
    ]


# ── MPC fetch (optional) ──────────────────────────────────────────
def fetch_mpc_comets():
    """
    Fetch current observable comets from MPC.
    Returns list of comets with approximate positions.
    """
    print("  Fetching comet data from MPC...")
    url = (
        "https://minorplanetcenter.net/iau/"
        "Ephemerides/Comets/Soft00Cmt.txt"
    )

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        lines  = response.text.strip().split("\n")
        comets = []

        for line in lines:
            if len(line) < 100:
                continue
            try:
                name = line[102:158].strip()
                if not name:
                    continue

                epoch_yr  = line[14:18].strip()
                epoch_mon = line[18:20].strip()
                epoch_day = line[20:25].strip()

                if not epoch_yr or not epoch_mon:
                    continue

                comets.append({
                    "name":        name,
                    "designation": line[0:11].strip(),
                    "type":        "MPC Listed",
                    "notes":       "Currently observable",
                    "epoch":       (
                        f"{epoch_yr}-{epoch_mon}"
                        f"-{epoch_day[:2]}"
                    )
                })

            except Exception:
                continue

        print(f"  Found {len(comets)} MPC comets")
        return comets

    except Exception as e:
        print(f"  [ERROR] MPC fetch failed: {e}")
        return []


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Comet Tracker — May 2026\n")
    comets    = get_current_comets()
    trackable = [c for c in comets
                 if c.get("ra_deg") is not None]

    print(f"  Total comets:     {len(comets)}")
    print(f"  Trackable:        {len(trackable)}")
    print()

    # Test from Mauna Kea
    lat, lon = 19.8207, -155.4681

    print(f"  {'Comet':<35} {'Mag':<6} "
          f"{'Visibility':<30} Status")
    print("  " + "─" * 90)

    for comet in comets:
        vis     = get_comet_visibility(comet, lat, lon)
        vis_str = (
            f"Alt {vis['altitude']}° — "
            f"{'VISIBLE' if vis['visible'] else 'below horizon'}"
            if vis else "No position data"
        )
        print(
            f"  {comet['name']:<35} "
            f"{comet['magnitude']:<6} "
            f"{vis_str:<30} "
            f"{comet['status'][:25]}"
        )
    print()