from datetime import datetime, date, timedelta


# ── Complete meteor shower catalogue ─────────────────────────────
METEOR_SHOWERS = [
    {
        "name":         "Quadrantids",
        "peak_date":    "January 3",
        "peak_month":   1,
        "peak_day":     3,
        "active_start": "January 1",
        "active_end":   "January 5",
        "zhr":          120,
        "speed_km_s":   41,
        "radiant_ra":   230,
        "radiant_dec":  49,
        "parent":       "Asteroid 2003 EH1",
        "description":  (
            "One of the strongest showers of the year "
            "but with a very narrow peak of only 6 hours. "
            "Rich in faint meteors with occasional fireballs. "
            "Best viewed from Northern Hemisphere."
        ),
        "best_time":    "Pre-dawn",
        "hemisphere":   "Northern",
        "color":        "#378ADD",
        "emoji":        "❄️"
    },
    {
        "name":         "Lyrids",
        "peak_date":    "April 22",
        "peak_month":   4,
        "peak_day":     22,
        "active_start": "April 16",
        "active_end":   "April 25",
        "zhr":          18,
        "speed_km_s":   49,
        "radiant_ra":   271,
        "radiant_dec":  34,
        "parent":       "Comet C/1861 G1 Thatcher",
        "description":  (
            "One of the oldest recorded meteor showers "
            "observed for over 2700 years. Fast meteors "
            "with persistent trains. Occasional outbursts "
            "to 100 ZHR have been recorded."
        ),
        "best_time":    "Pre-dawn",
        "hemisphere":   "Both",
        "color":        "#9B59B6",
        "emoji":        "🌸"
    },
    {
        "name":         "Eta Aquariids",
        "peak_date":    "May 6",
        "peak_month":   5,
        "peak_day":     6,
        "active_start": "April 19",
        "active_end":   "May 28",
        "zhr":          50,
        "speed_km_s":   66,
        "radiant_ra":   338,
        "radiant_dec":  -1,
        "parent":       "1P/Halley",
        "description":  (
            "Debris from Halley's Comet. Very fast meteors "
            "leaving persistent glowing trains. Best from "
            "Southern Hemisphere where the radiant rises "
            "much higher in the sky."
        ),
        "best_time":    "Pre-dawn",
        "hemisphere":   "Southern",
        "color":        "#1D9E75",
        "emoji":        "💧"
    },
    {
        "name":         "Delta Aquariids",
        "peak_date":    "July 30",
        "peak_month":   7,
        "peak_day":     30,
        "active_start": "July 12",
        "active_end":   "August 23",
        "zhr":          25,
        "speed_km_s":   41,
        "radiant_ra":   339,
        "radiant_dec":  -16,
        "parent":       "Comet 96P/Machholz",
        "description":  (
            "Long active period makes this a reliable "
            "summer shower. Best from tropics and "
            "Southern Hemisphere. Often confused with "
            "early Perseids in July and August."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Southern",
        "color":        "#E67E22",
        "emoji":        "☀️"
    },
    {
        "name":         "Perseids",
        "peak_date":    "August 12",
        "peak_month":   8,
        "peak_day":     12,
        "active_start": "July 17",
        "active_end":   "August 24",
        "zhr":          100,
        "speed_km_s":   59,
        "radiant_ra":   48,
        "radiant_dec":  58,
        "parent":       "109P/Swift-Tuttle",
        "description":  (
            "The most popular meteor shower of the year. "
            "Reliable, prolific, warm summer nights. "
            "Fast bright meteors with persistent trains "
            "and frequent fireballs. A must-see event."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Northern",
        "color":        "#E74C3C",
        "emoji":        "🔥"
    },
    {
        "name":         "Orionids",
        "peak_date":    "October 21",
        "peak_month":   10,
        "peak_day":     21,
        "active_start": "October 2",
        "active_end":   "November 7",
        "zhr":          20,
        "speed_km_s":   66,
        "radiant_ra":   95,
        "radiant_dec":  16,
        "parent":       "1P/Halley",
        "description":  (
            "Second Halley shower of the year. "
            "Very fast meteors leaving long glowing trains. "
            "Active for over a month with a broad flat peak. "
            "Visible from both hemispheres."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Both",
        "color":        "#F39C12",
        "emoji":        "🍂"
    },
    {
        "name":         "Draconids",
        "peak_date":    "October 8",
        "peak_month":   10,
        "peak_day":     8,
        "active_start": "October 6",
        "active_end":   "October 10",
        "zhr":          10,
        "speed_km_s":   20,
        "radiant_ra":   262,
        "radiant_dec":  54,
        "parent":       "21P/Giacobini-Zinner",
        "description":  (
            "Usually minor but produced spectacular "
            "storms in 1933 and 1946. Slowest meteors "
            "of any major shower. Best in evening. "
            "Unpredictable — watch for outbursts."
        ),
        "best_time":    "Evening",
        "hemisphere":   "Northern",
        "color":        "#5DADE2",
        "emoji":        "🐉"
    },
    {
        "name":         "Taurids",
        "peak_date":    "November 5",
        "peak_month":   11,
        "peak_day":     5,
        "active_start": "October 1",
        "active_end":   "November 25",
        "zhr":          10,
        "speed_km_s":   27,
        "radiant_ra":   58,
        "radiant_dec":  14,
        "parent":       "2P/Encke",
        "description":  (
            "Long active period over 7 weeks. "
            "Low ZHR but famous for spectacular "
            "fireballs and bolides. Split into North "
            "and South branches. Halloween fireballs."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Both",
        "color":        "#E67E22",
        "emoji":        "🎃"
    },
    {
        "name":         "Leonids",
        "peak_date":    "November 17",
        "peak_month":   11,
        "peak_day":     17,
        "active_start": "November 6",
        "active_end":   "November 30",
        "zhr":          15,
        "speed_km_s":   71,
        "radiant_ra":   152,
        "radiant_dec":  22,
        "parent":       "55P/Tempel-Tuttle",
        "description":  (
            "Fastest meteors of any annual shower at "
            "71 km/s. Historic storms every 33 years — "
            "next potential storm 2034. Vivid colours "
            "and long persistent trains."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Both",
        "color":        "#FFD700",
        "emoji":        "🦁"
    },
    {
        "name":         "Geminids",
        "peak_date":    "December 14",
        "peak_month":   12,
        "peak_day":     14,
        "active_start": "December 4",
        "active_end":   "December 17",
        "zhr":          150,
        "speed_km_s":   35,
        "radiant_ra":   112,
        "radiant_dec":  33,
        "parent":       "Asteroid 3200 Phaethon",
        "description":  (
            "The best meteor shower of the year. "
            "Highest ZHR of any annual shower. "
            "Unique — caused by an asteroid not a comet. "
            "Bright multicoloured meteors visible all night."
        ),
        "best_time":    "All night",
        "hemisphere":   "Both",
        "color":        "#1D9E75",
        "emoji":        "♊"
    },
    {
        "name":         "Ursids",
        "peak_date":    "December 22",
        "peak_month":   12,
        "peak_day":     22,
        "active_start": "December 17",
        "active_end":   "December 26",
        "zhr":          10,
        "speed_km_s":   33,
        "radiant_ra":   217,
        "radiant_dec":  76,
        "parent":       "8P/Tuttle",
        "description":  (
            "Circumpolar shower for Northern Hemisphere. "
            "Radiant near Polaris so visible all night. "
            "Occasional outbursts to 50 ZHR. "
            "Coincides with winter solstice."
        ),
        "best_time":    "All night",
        "hemisphere":   "Northern",
        "color":        "#AFA9EC",
        "emoji":        "🐻"
    },
    {
        "name":         "Puppid-Velids",
        "peak_date":    "December 7",
        "peak_month":   12,
        "peak_day":     7,
        "active_start": "December 1",
        "active_end":   "December 15",
        "zhr":          10,
        "speed_km_s":   40,
        "radiant_ra":   123,
        "radiant_dec":  -45,
        "parent":       "Unknown",
        "description":  (
            "Southern hemisphere shower with multiple "
            "radiants in Puppis and Vela. Invisible from "
            "mid-northern latitudes. Good for southern "
            "observers in December."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Southern",
        "color":        "#27AE60",
        "emoji":        "🌍"
    },
    {
        "name":         "Virginids",
        "peak_date":    "April 10",
        "peak_month":   4,
        "peak_day":     10,
        "active_start": "March 5",
        "active_end":   "April 21",
        "zhr":          5,
        "speed_km_s":   30,
        "radiant_ra":   195,
        "radiant_dec":  0,
        "parent":       "Unknown",
        "description":  (
            "Complex of showers in Virgo active for "
            "six weeks in spring. Low ZHR but long "
            "active period. Slow to medium speed meteors."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Both",
        "color":        "#EC407A",
        "emoji":        "♍"
    },
    {
        "name":         "Capricornids",
        "peak_date":    "July 15",
        "peak_month":   7,
        "peak_day":     15,
        "active_start": "July 3",
        "active_end":   "August 15",
        "zhr":          5,
        "speed_km_s":   23,
        "radiant_ra":   315,
        "radiant_dec":  -15,
        "parent":       "Comet 169P/NEAT",
        "description":  (
            "Slow meteors with many bright fireballs. "
            "Best from Southern Hemisphere but visible "
            "worldwide. Often produces yellow and orange "
            "coloured meteors."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Southern",
        "color":        "#FF8C00",
        "emoji":        "♑"
    },
    {
        "name":         "Piscis Austrinids",
        "peak_date":    "July 28",
        "peak_month":   7,
        "peak_day":     28,
        "active_start": "July 15",
        "active_end":   "August 10",
        "zhr":          5,
        "speed_km_s":   35,
        "radiant_ra":   341,
        "radiant_dec":  -30,
        "parent":       "Unknown",
        "description":  (
            "Southern shower best seen from Southern "
            "Hemisphere. Active for nearly a month. "
            "Medium speed meteors with some fireballs."
        ),
        "best_time":    "After midnight",
        "hemisphere":   "Southern",
        "color":        "#26C6DA",
        "emoji":        "🐟"
    },
]


# ── Helper functions ──────────────────────────────────────────────
MONTH_NAMES = {
    "January": 1,  "February": 2,  "March": 3,
    "April": 4,    "May": 5,       "June": 6,
    "July": 7,     "August": 8,    "September": 9,
    "October": 10, "November": 11, "December": 12
}

def parse_date_str(date_str, year):
    """Parse 'Month Day' string to date object."""
    parts = date_str.strip().split()
    month = MONTH_NAMES[parts[0]]
    day   = int(parts[1])
    return date(year, month, day)

def get_days_until_peak(shower, year=None):
    """Calculate days until next peak."""
    if year is None:
        year  = datetime.utcnow().year
    today = date.today()
    peak  = date(year, shower["peak_month"],
                 shower["peak_day"])
    if peak < today:
        peak = date(year + 1,
                    shower["peak_month"],
                    shower["peak_day"])
    return (peak - today).days

def is_active(shower, year=None):
    """Check if shower is currently active."""
    if year is None:
        year  = datetime.utcnow().year
    today = date.today()
    try:
        start = parse_date_str(
            shower["active_start"], year)
        end   = parse_date_str(
            shower["active_end"], year)
        if end < start:
            end = parse_date_str(
                shower["active_end"], year + 1)
        return start <= today <= end
    except Exception:
        return False

def is_at_peak(shower, year=None):
    """Check if shower is within 1 day of peak."""
    return get_days_until_peak(shower, year) <= 1

def get_shower_status(shower):
    """Get current status string and color."""
    if is_at_peak(shower):
        return "🔥 AT PEAK NOW", "#E74C3C"
    elif is_active(shower):
        days = get_days_until_peak(shower)
        if days <= 3:
            return f"⚡ Peak in {days}d", "#EF9F27"
        else:
            return "✅ Active now", "#1D9E75"
    else:
        days = get_days_until_peak(shower)
        if days <= 14:
            return f"📅 In {days} days", "#378ADD"
        elif days <= 30:
            return f"🔜 In {days} days", "#9B59B6"
        else:
            return f"💤 In {days} days", "#888888"

def get_zhr_quality(zhr):
    """Rate ZHR value."""
    if zhr >= 100:  return "Exceptional", "#E74C3C"
    elif zhr >= 50: return "Excellent",   "#EF9F27"
    elif zhr >= 25: return "Good",        "#1D9E75"
    elif zhr >= 10: return "Moderate",    "#378ADD"
    else:           return "Minor",       "#888888"

def get_speed_rating(speed):
    """Rate meteor speed."""
    if speed >= 60:   return "Extremely fast"
    elif speed >= 45: return "Fast"
    elif speed >= 30: return "Medium"
    else:             return "Slow"

def get_all_showers_sorted():
    """Get all showers sorted by days until peak."""
    result = []
    for shower in METEOR_SHOWERS:
        days          = get_days_until_peak(shower)
        status, color = get_shower_status(shower)
        zhr_q, zhr_c  = get_zhr_quality(shower["zhr"])
        result.append({
            **shower,
            "days_until_peak": days,
            "status":          status,
            "status_color":    color,
            "is_active":       is_active(shower),
            "is_at_peak":      is_at_peak(shower),
            "zhr_quality":     zhr_q,
            "zhr_color":       zhr_c,
            "speed_rating":    get_speed_rating(
                shower["speed_km_s"])
        })
    return sorted(result,
                  key=lambda x: x["days_until_peak"])

def get_active_showers():
    """Get currently active showers."""
    return [s for s in get_all_showers_sorted()
            if s["is_active"]]

def get_upcoming_showers(days_ahead=60):
    """Get showers peaking in the next N days."""
    return [s for s in get_all_showers_sorted()
            if s["days_until_peak"] <= days_ahead]

def get_year_calendar(year=None):
    """
    Get all showers organised by month for the year.
    """
    if year is None:
        year = datetime.utcnow().year

    months = {i: [] for i in range(1, 13)}
    for shower in METEOR_SHOWERS:
        months[shower["peak_month"]].append(shower)
    return months

def moon_phase_on_peak(shower, year=None):
    """
    Estimate moon phase on peak night.
    Returns phase percentage (0=new, 100=full).
    """
    try:
        import ephem
        if year is None:
            year = datetime.utcnow().year
        peak_date = date(
            year, shower["peak_month"],
            shower["peak_day"])
        moon      = ephem.Moon(
            peak_date.strftime("%Y/%m/%d"))
        return round(moon.phase, 1)
    except Exception:
        return None

def observing_score(shower, year=None):
    """
    Score how good this shower will be to observe.
    Considers ZHR, moon phase, speed.
    Returns 0-100.
    """
    zhr_score   = min(100, shower["zhr"])
    moon        = moon_phase_on_peak(shower, year)
    moon_penalty = (moon / 100 * 40) if moon else 20
    speed_bonus  = min(20, shower["speed_km_s"] / 4)
    score        = max(0, min(100,
        zhr_score * 0.6
        - moon_penalty
        + speed_bonus
    ))
    return round(score, 1)


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n  Meteor Shower Calendar")
    print(f"  Total showers: {len(METEOR_SHOWERS)}\n")

    showers = get_all_showers_sorted()

    print(f"  {'Shower':<20} {'Peak':<15} "
          f"{'ZHR':<6} {'Days':<8} {'Status'}")
    print("  " + "─" * 65)

    for s in showers:
        print(
            f"  {s['emoji']} {s['name']:<18} "
            f"{s['peak_date']:<15} "
            f"{s['zhr']:<6} "
            f"{s['days_until_peak']:<8} "
            f"{s['status']}"
        )

    print()
    active = get_active_showers()
    if active:
        print(f"  Currently active:")
        for s in active:
            print(f"    {s['emoji']} {s['name']} "
                  f"— peaks {s['peak_date']}")
    else:
        print("  No showers currently active")

    upcoming = get_upcoming_showers(30)
    print(f"\n  Next 30 days: "
          f"{len(upcoming)} showers\n")