from datetime import datetime, date, timedelta
import math
import ephem

# ── Eclipse and transit catalogue ─────────────────────────────────
# Data from NASA Eclipse Website (Espenak & Meeus)
# All times in UTC

SOLAR_ECLIPSES = [
    {
        "date":          "2025-03-29",
        "type":          "Partial Solar",
        "subtype":       "partial",
        "magnitude":     0.938,
        "duration_mins": 0,
        "path_lat_start": 0,
        "path_lon_start": 0,
        "path_lat_end":   0,
        "path_lon_end":   0,
        "center_lat":    67.0,
        "center_lon":    -29.0,
        "gamma":          1.040,
        "regions":       "NW Africa, Europe, N Russia",
        "totality_path": [],
        "description":   (
            "Partial solar eclipse visible across "
            "northwest Africa, Europe and northern Russia. "
            "Maximum eclipse occurs over the North Atlantic."
        ),
        "color":         "#EF9F27",
        "emoji":         "🌘"
    },
    {
        "date":          "2025-09-21",
        "type":          "Partial Solar",
        "subtype":       "partial",
        "magnitude":     0.855,
        "duration_mins": 0,
        "center_lat":    -71.0,
        "center_lon":    150.0,
        "gamma":          -1.065,
        "regions":       "S Australia, Antarctica, Pacific",
        "totality_path": [],
        "description":   (
            "Partial solar eclipse visible from "
            "southern Australia, New Zealand and "
            "Antarctica."
        ),
        "color":         "#EF9F27",
        "emoji":         "🌘"
    },
    {
        "date":          "2026-02-17",
        "type":          "Annular Solar",
        "subtype":       "annular",
        "magnitude":     0.963,
        "duration_mins": 2,
        "center_lat":    -62.0,
        "center_lon":    -80.0,
        "gamma":          -0.975,
        "regions":       "Antarctica, S South America",
        "totality_path": [
            (-60, -90), (-62, -80), (-64, -70),
            (-66, -60), (-68, -50)
        ],
        "description":   (
            "Annular solar eclipse ('ring of fire') "
            "visible from Antarctica and the southern "
            "tip of South America."
        ),
        "color":         "#F39C12",
        "emoji":         "💍"
    },
    {
        "date":          "2026-08-12",
        "type":          "Total Solar",
        "subtype":       "total",
        "magnitude":     1.079,
        "duration_mins": 2.3,
        "center_lat":    37.0,
        "center_lon":    -3.0,
        "gamma":          0.896,
        "regions":       "Arctic, Greenland, Iceland, Spain, Algeria",
        "totality_path": [
            (78, -40), (72, -30), (65, -20),
            (58, -12), (50, -8), (42, -5),
            (37, -3), (32, 2), (28, 5)
        ],
        "description":   (
            "Total solar eclipse with a path of totality "
            "crossing the Arctic, Greenland, Iceland, "
            "the Faroe Islands, Spain and Algeria. "
            "Maximum totality lasts 2m 18s near Valencia, Spain."
        ),
        "color":         "#E74C3C",
        "emoji":         "🌑"
    },
    {
        "date":          "2027-02-06",
        "type":          "Annular Solar",
        "subtype":       "annular",
        "magnitude":     0.928,
        "duration_mins": 7.5,
        "center_lat":    -25.0,
        "center_lon":    -10.0,
        "gamma":          -0.297,
        "regions":       "S America, Atlantic, Africa",
        "totality_path": [
            (-15, -50), (-20, -35), (-25, -20),
            (-28, -10), (-30, 0), (-32, 10)
        ],
        "description":   (
            "Annular solar eclipse crossing South America, "
            "the Atlantic Ocean and Africa. "
            "Duration of annularity up to 7m 51s."
        ),
        "color":         "#F39C12",
        "emoji":         "💍"
    },
    {
        "date":          "2027-08-02",
        "type":          "Total Solar",
        "subtype":       "total",
        "magnitude":     1.079,
        "duration_mins": 6.2,
        "center_lat":    25.0,
        "center_lon":    30.0,
        "gamma":          0.145,
        "regions":       "Morocco, Spain, Algeria, Libya, Egypt, Saudi Arabia, Yemen, Somalia",
        "totality_path": [
            (30, -10), (32, 0), (32, 10),
            (30, 20), (28, 30), (25, 40),
            (22, 48), (18, 52), (12, 50)
        ],
        "description":   (
            "One of the longest total solar eclipses of "
            "the 21st century. Maximum totality of 6m 23s "
            "occurs over Egypt and the Red Sea. "
            "Path crosses Morocco, Algeria, Tunisia, Libya, "
            "Egypt, Saudi Arabia and Yemen."
        ),
        "color":         "#E74C3C",
        "emoji":         "🌑"
    },
    {
        "date":          "2028-01-26",
        "type":          "Annular Solar",
        "subtype":       "annular",
        "magnitude":     0.970,
        "duration_mins": 10.3,
        "center_lat":    -28.0,
        "center_lon":    130.0,
        "gamma":          -0.391,
        "regions":       "Ecuador, Peru, Brazil, Spain, Portugal",
        "totality_path": [
            (-10, -80), (-18, -65), (-25, -50),
            (-30, -35), (-33, -20), (-34, -10)
        ],
        "description":   (
            "Annular solar eclipse with long duration "
            "annularity. Path crosses Ecuador, Peru "
            "and Brazil before ending in the Atlantic."
        ),
        "color":         "#F39C12",
        "emoji":         "💍"
    },
    {
        "date":          "2028-07-22",
        "type":          "Total Solar",
        "subtype":       "total",
        "magnitude":     1.056,
        "duration_mins": 5.1,
        "center_lat":    -28.0,
        "center_lon":    135.0,
        "gamma":          -0.498,
        "regions":       "Australia, New Zealand",
        "totality_path": [
            (-20, 110), (-25, 120), (-28, 130),
            (-30, 140), (-32, 150), (-35, 160),
            (-38, 170), (-42, 178)
        ],
        "description":   (
            "Total solar eclipse crossing Australia "
            "from west to east, passing through "
            "Western Australia, South Australia and "
            "New South Wales before ending in the "
            "Tasman Sea near New Zealand."
        ),
        "color":         "#E74C3C",
        "emoji":         "🌑"
    },
    {
        "date":          "2030-06-01",
        "type":          "Annular Solar",
        "subtype":       "annular",
        "magnitude":     0.944,
        "duration_mins": 5.8,
        "center_lat":    52.0,
        "center_lon":    90.0,
        "gamma":          0.520,
        "regions":       "Algeria, Tunisia, Greece, Turkey, Russia, China, Japan",
        "totality_path": [
            (35, 0), (38, 15), (42, 30),
            (46, 50), (50, 70), (52, 90),
            (52, 110), (50, 130)
        ],
        "description":   (
            "Annular eclipse crossing North Africa, "
            "southern Europe, Russia and China."
        ),
        "color":         "#F39C12",
        "emoji":         "💍"
    },
    {
        "date":          "2030-11-25",
        "type":          "Total Solar",
        "subtype":       "total",
        "magnitude":     1.047,
        "duration_mins": 3.7,
        "center_lat":    -32.0,
        "center_lon":    20.0,
        "gamma":          -0.358,
        "regions":       "Namibia, Botswana, South Africa, Australia",
        "totality_path": [
            (-20, 10), (-25, 15), (-30, 20),
            (-33, 25), (-35, 30), (-37, 35)
        ],
        "description":   (
            "Total solar eclipse crossing southern "
            "Africa and the Indian Ocean."
        ),
        "color":         "#E74C3C",
        "emoji":         "🌑"
    },
]

LUNAR_ECLIPSES = [
    {
        "date":              "2025-03-14",
        "type":              "Total Lunar",
        "subtype":           "total",
        "magnitude":         1.178,
        "penumbral_start":   "03:57",
        "partial_start":     "05:09",
        "totality_start":    "06:26",
        "max_eclipse":       "06:58",
        "totality_end":      "07:31",
        "partial_end":       "08:48",
        "penumbral_end":     "10:00",
        "duration_totality": 65,
        "duration_partial":  219,
        "visible_regions":   "Americas, Europe, Africa, W Asia",
        "color":             "#E74C3C",
        "emoji":             "🔴",
        "description":       (
            "Total lunar eclipse — the Moon turns "
            "a deep red/orange colour during totality. "
            "Visible from the Americas, Europe, Africa "
            "and western Asia. Totality lasts 65 minutes."
        )
    },
    {
        "date":              "2025-09-07",
        "type":              "Total Lunar",
        "subtype":           "total",
        "magnitude":         1.361,
        "penumbral_start":   "15:27",
        "partial_start":     "16:29",
        "totality_start":    "17:30",
        "max_eclipse":       "18:11",
        "totality_end":      "18:52",
        "partial_end":       "19:54",
        "penumbral_end":     "20:56",
        "duration_totality": 82,
        "duration_partial":  205,
        "visible_regions":   "Europe, Africa, Asia, Australia",
        "color":             "#E74C3C",
        "emoji":             "🔴",
        "description":       (
            "Deep total lunar eclipse with magnitude 1.361. "
            "The Moon will appear very dark red during "
            "totality. Visible from Europe, Africa, Asia "
            "and Australia. Totality lasts 82 minutes."
        )
    },
    {
        "date":              "2026-03-03",
        "type":              "Total Lunar",
        "subtype":           "total",
        "magnitude":         1.150,
        "penumbral_start":   "21:48",
        "partial_start":     "22:42",
        "totality_start":    "23:42",
        "max_eclipse":       "00:33",
        "totality_end":      "01:23",
        "partial_end":       "02:23",
        "penumbral_end":     "03:17",
        "duration_totality": 61,
        "duration_partial":  221,
        "visible_regions":   "Pacific, Americas, W Europe, W Africa",
        "color":             "#E74C3C",
        "emoji":             "🔴",
        "description":       (
            "Total lunar eclipse visible from the Pacific, "
            "Americas, western Europe and western Africa."
        )
    },
    {
        "date":              "2026-08-28",
        "type":              "Partial Lunar",
        "subtype":           "partial",
        "magnitude":         0.931,
        "penumbral_start":   "02:22",
        "partial_start":     "03:13",
        "totality_start":    None,
        "max_eclipse":       "04:13",
        "totality_end":      None,
        "partial_end":       "05:14",
        "penumbral_end":     "06:05",
        "duration_totality": 0,
        "duration_partial":  121,
        "visible_regions":   "Pacific, Americas, Europe, Africa, W Asia",
        "color":             "#EF9F27",
        "emoji":             "🌔",
        "description":       (
            "Deep partial lunar eclipse where 93% of "
            "the Moon enters Earth's shadow. "
            "Will appear very dark on one side."
        )
    },
    {
        "date":              "2028-07-06",
        "type":              "Total Lunar",
        "subtype":           "total",
        "magnitude":         1.700,
        "penumbral_start":   "13:24",
        "partial_start":     "14:24",
        "totality_start":    "15:30",
        "max_eclipse":       "16:20",
        "totality_end":      "17:11",
        "partial_end":       "18:17",
        "penumbral_end":     "19:18",
        "duration_totality": 101,
        "duration_partial":  233,
        "visible_regions":   "Europe, Africa, Asia, Australia",
        "color":             "#E74C3C",
        "emoji":             "🔴",
        "description":       (
            "Very deep total lunar eclipse with magnitude "
            "1.700 — one of the deepest of the century. "
            "The Moon will appear very dark red, possibly "
            "dark brown during totality. "
            "Totality lasts 101 minutes."
        )
    },
    {
        "date":              "2029-12-31",
        "type":              "Total Lunar",
        "subtype":           "total",
        "magnitude":         1.116,
        "penumbral_start":   "20:01",
        "partial_start":     "21:01",
        "totality_start":    "22:07",
        "max_eclipse":       "22:52",
        "totality_end":      "23:37",
        "partial_end":       "00:43",
        "penumbral_end":     "01:43",
        "duration_totality": 90,
        "duration_partial":  222,
        "visible_regions":   "Americas, Europe, Africa, W Asia",
        "color":             "#E74C3C",
        "emoji":             "🔴",
        "description":       (
            "Total lunar eclipse on New Year's Eve 2029. "
            "Visible from the Americas, Europe, "
            "Africa and western Asia."
        )
    },
]

TRANSITS = [
    {
        "date":         "2032-11-13",
        "type":         "Mercury Transit",
        "subtype":      "mercury",
        "start":        "06:41",
        "mid":          "10:00",
        "end":          "13:18",
        "duration_hrs": 6.6,
        "description":  (
            "Mercury crosses the face of the Sun. "
            "Requires a solar telescope or solar filter. "
            "Mercury appears as a tiny black dot "
            "crossing the solar disc. "
            "Visible from Europe, Africa, Asia and Australia."
        ),
        "visible_regions": "Europe, Africa, Asia, Australia",
        "color":        "#378ADD",
        "emoji":        "☿",
        "rarity":       "Every 7-13 years"
    },
    {
        "date":         "2039-11-07",
        "type":         "Mercury Transit",
        "subtype":      "mercury",
        "start":        "08:05",
        "mid":          "11:10",
        "end":          "14:14",
        "duration_hrs": 6.2,
        "description":  (
            "Mercury transit across the Sun. "
            "Requires a solar telescope or solar filter."
        ),
        "visible_regions": "Americas, Europe, Africa",
        "color":        "#378ADD",
        "emoji":        "☿",
        "rarity":       "Every 7-13 years"
    },
    {
        "date":         "2117-12-11",
        "type":         "Venus Transit",
        "subtype":      "venus",
        "start":        "23:58",
        "mid":          "02:48",
        "end":          "05:38",
        "duration_hrs": 5.7,
        "description":  (
            "Venus transit — one of the rarest predictable "
            "astronomical events. Venus appears as a "
            "large black dot crossing the Sun. "
            "The last Venus transit was June 5-6 2012. "
            "Nobody alive today will see this one."
        ),
        "visible_regions": "Most of Earth",
        "color":        "#9B59B6",
        "emoji":        "♀",
        "rarity":       "Pairs every 105-121 years"
    },
]


# ── Helper functions ──────────────────────────────────────────────
def get_days_until(date_str):
    """Days until an eclipse/transit date."""
    today      = date.today()
    event_date = datetime.strptime(
        date_str, "%Y-%m-%d").date()
    delta      = (event_date - today).days
    return delta


def is_past(date_str):
    """Check if event has already passed."""
    return get_days_until(date_str) < 0


def get_upcoming_events(days_ahead=3650):
    """Get all upcoming eclipses and transits sorted by date."""
    events = []

    for e in SOLAR_ECLIPSES:
        days = get_days_until(e["date"])
        if days >= 0:
            events.append({
                **e,
                "category":       "Solar Eclipse",
                "days_until":     days,
                "date_display":   datetime.strptime(
                    e["date"], "%Y-%m-%d"
                ).strftime("%B %d, %Y"),
            })

    for e in LUNAR_ECLIPSES:
        days = get_days_until(e["date"])
        if days >= 0:
            events.append({
                **e,
                "category":       "Lunar Eclipse",
                "days_until":     days,
                "date_display":   datetime.strptime(
                    e["date"], "%Y-%m-%d"
                ).strftime("%B %d, %Y"),
            })

    for e in TRANSITS:
        days = get_days_until(e["date"])
        if days >= 0:
            events.append({
                **e,
                "category":       "Transit",
                "days_until":     days,
                "date_display":   datetime.strptime(
                    e["date"], "%Y-%m-%d"
                ).strftime("%B %d, %Y"),
            })

    return sorted(events, key=lambda x: x["days_until"])


def get_eclipse_visibility(eclipse, lat, lon, alt_m=0):
    """
    Check if a solar or lunar eclipse is visible
    from a given location.
    Returns visibility dict.
    """
    try:
        observer           = ephem.Observer()
        observer.lat       = str(lat)
        observer.long      = str(lon)
        observer.elevation = float(alt_m)
        observer.pressure  = 0

        date_str = eclipse["date"]
        category = eclipse.get("category", "")

        if "Lunar" in category or "Lunar" in eclipse.get("type", ""):
            # For lunar eclipses check Moon altitude
            # at time of maximum
            max_time = eclipse.get("max_eclipse", "00:00")
            dt_str   = f"{date_str} {max_time}"
            try:
                observer.date = ephem.Date(dt_str)
            except Exception:
                observer.date = ephem.Date(date_str)

            moon = ephem.Moon()
            moon.compute(observer)
            moon_alt = math.degrees(float(moon.alt))
            moon_az  = math.degrees(float(moon.az))

            sun = ephem.Sun()
            sun.compute(observer)
            sun_alt = math.degrees(float(sun.alt))

            visible = moon_alt > 10 and sun_alt < 0

            return {
                "visible":    visible,
                "moon_alt":   round(moon_alt, 1),
                "moon_az":    round(moon_az, 1),
                "sun_alt":    round(sun_alt, 1),
                "reason":     (
                    "Moon above horizon during eclipse"
                    if visible
                    else "Moon below horizon at maximum"
                    if moon_alt <= 10
                    else "Sun above horizon — daytime"
                )
            }

        elif "Solar" in category or "Solar" in eclipse.get("type", ""):
            # For solar eclipses check Sun altitude at noon
            dt_str = f"{date_str} 12:00:00"
            try:
                observer.date = ephem.Date(dt_str)
            except Exception:
                observer.date = ephem.Date(date_str)

            sun = ephem.Sun()
            sun.compute(observer)
            sun_alt = math.degrees(float(sun.alt))
            sun_az  = math.degrees(float(sun.az))

            # Check if location is in roughly
            # correct hemisphere for the eclipse
            center_lat = eclipse.get("center_lat", 0)
            center_lon = eclipse.get("center_lon", 0)

            lat_diff = abs(float(lat) - center_lat)
            lon_diff = abs(float(lon) - center_lon)

            # Simple visibility estimate
            # based on geometry
            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            roughly_visible = (
                lat_diff < 75 and lon_diff < 100
                and sun_alt > 10
            )

            # Check if inside totality path
            in_path = False
            subtype = eclipse.get("subtype", "")
            if subtype in ["total", "annular"]:
                path = eclipse.get("totality_path", [])
                if path:
                    for pt_lat, pt_lon in path:
                        if (abs(float(lat) - pt_lat) < 5 and
                                abs(float(lon) - pt_lon) < 8):
                            in_path = True
                            break

            return {
                "visible":         roughly_visible,
                "in_totality_path": in_path,
                "sun_alt":         round(sun_alt, 1),
                "sun_az":          round(sun_az, 1),
                "eclipse_type":    subtype,
                "reason":          (
                    "Inside path of totality!"
                    if in_path
                    else "Partial eclipse visible"
                    if roughly_visible
                    else "Not visible from this location"
                )
            }

        return {"visible": False, "reason": "Unknown eclipse type"}

    except Exception as e:
        return {"visible": False, "reason": str(e)}


def get_best_observatories_for_eclipse(
    eclipse, df, max_obs=20
):
    """
    Find the best observatories to observe
    an eclipse from, combining visibility
    and weather score.
    """
    results = []

    # Sample every 5th for speed
    sample = df.iloc[::3]

    for _, row in sample.iterrows():
        vis = get_eclipse_visibility(
            eclipse,
            float(row["latitude"]),
            float(row["longitude"]),
            float(row.get("altitude_m", 0) or 0)
        )

        if vis["visible"]:
            results.append({
                "observatory":    row["observatory"],
                "country":        row["country"],
                "latitude":       row["latitude"],
                "longitude":      row["longitude"],
                "altitude_m":     row.get("altitude_m", 0),
                "weather_score":  row["observation_score"],
                "in_totality":    vis.get(
                    "in_totality_path", False),
                "visibility":     vis,
                "combined_score": (
                    row["observation_score"] * 0.6 +
                    (40 if vis.get(
                        "in_totality_path") else 0)
                )
            })

    results.sort(
        key=lambda x: x["combined_score"],
        reverse=True
    )
    return results[:max_obs]


def eclipse_rarity(eclipse):
    """Describe how rare this eclipse is."""
    subtype = eclipse.get("subtype", "")
    if subtype == "total":
        return "Rare — total solar eclipses visible from any given location only once every 375 years on average"
    elif subtype == "annular":
        return "Uncommon — annular eclipses occur about as often as total eclipses"
    elif subtype == "mercury":
        return "Uncommon — Mercury transits occur 13-14 times per century"
    elif subtype == "venus":
        return "Extremely rare — Venus transits occur in pairs separated by 8 years, then gaps of 105-121 years"
    else:
        return "Partial eclipses are relatively common — several per year worldwide"


def get_all_past_recent():
    """Get recently past eclipses for reference."""
    events = []
    for e in SOLAR_ECLIPSES + LUNAR_ECLIPSES + TRANSITS:
        days = get_days_until(e["date"])
        if -365 <= days < 0:
            events.append({
                **e,
                "days_until":   days,
                "date_display": datetime.strptime(
                    e["date"], "%Y-%m-%d"
                ).strftime("%B %d, %Y")
            })
    return sorted(
        events, key=lambda x: x["days_until"],
        reverse=True)


if __name__ == "__main__":
    print("\n  Eclipse & Transit Tracker\n")

    events = get_upcoming_events()
    print(f"  Upcoming events: {len(events)}\n")

    print(f"  {'Date':<15} {'Type':<25} "
          f"{'Days':<8} Category")
    print("  " + "─" * 60)

    for e in events[:10]:
        print(
            f"  {e['date']:<15} "
            f"{e['type']:<25} "
            f"{e['days_until']:<8} "
            f"{e['category']}"
        )
    print()