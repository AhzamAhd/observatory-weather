"""
User-submitted observatory suggestions.

Lets any user propose an observatory that's missing from GOWC. Submissions go to
a separate `observatory_suggestions` table --- they do NOT go straight into the
live `observatories` table, so unvetted entries can't pollute the site list or
the weather fetch. The site owner reviews pending suggestions and approves the
good ones (which then get added to observatories + the source JSON).

Mirrors the feedback module's pattern.
"""
import math
import pandas as pd
from datetime import datetime
from db import execute, query_df


def ensure_suggestions_table():
    """Create the suggestions table if it doesn't exist yet."""
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS observatory_suggestions (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                country     TEXT,
                latitude    REAL NOT NULL,
                longitude   REAL NOT NULL,
                altitude_m  REAL,
                notes       TEXT,
                contact     TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        return True
    except Exception:
        return False


def _valid_coords(lat, lon):
    return (lat is not None and lon is not None
            and -90 <= lat <= 90 and -180 <= lon <= 180)


def _duplicate_of(lat, lon, radius_km=15.0):
    """Return the name of an existing observatory within radius_km, or None.
    Prevents obvious duplicates being suggested."""
    try:
        df = query_df("SELECT name, latitude, longitude FROM observatories")
        if df.empty:
            return None
        d = ((df["latitude"] - lat) ** 2 + (df["longitude"] - lon) ** 2) ** 0.5
        nearest = df.iloc[d.idxmin()]
        if d.min() * 111.0 < radius_km:
            return nearest["name"]
        return None
    except Exception:
        return None


def add_suggestion(name, latitude, longitude, altitude_m=0.0,
                   country="", notes="", contact=""):
    """Store a single observatory suggestion. Validates coordinates and warns on
    likely duplicates, but still records them for the owner to judge."""
    name = (name or "").strip()
    if not name:
        return False, "Please give the observatory a name."
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False, "Latitude and longitude must be numbers."
    if not _valid_coords(latitude, longitude):
        return False, ("Coordinates out of range (latitude -90..90, "
                       "longitude -180..180).")

    dup = _duplicate_of(latitude, longitude)
    try:
        ensure_suggestions_table()
        execute("""
            INSERT INTO observatory_suggestions
                (name, country, latitude, longitude, altitude_m, notes,
                 contact, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
        """, [name, country, latitude, longitude, altitude_m or 0.0,
              notes, contact, datetime.utcnow()])
    except Exception as e:
        return False, f"Could not save suggestion: {e}"

    if dup:
        return True, (f"Thanks! Recorded. Note: a site already exists within "
                      f"~15 km (\"{dup}\") — the owner will check for "
                      "duplicates.")
    return True, "Thanks! Your observatory suggestion has been recorded."


def get_suggestions(status=None, limit=200):
    """Return suggestions (for the site owner). Optionally filter by status."""
    try:
        ensure_suggestions_table()
        if status:
            return query_df("""
                SELECT id, name, country, latitude, longitude, altitude_m,
                       notes, contact, status, created_at
                FROM observatory_suggestions
                WHERE status = %(s)s
                ORDER BY created_at DESC LIMIT %(lim)s
            """, {"s": status, "lim": limit})
        return query_df("""
            SELECT id, name, country, latitude, longitude, altitude_m,
                   notes, contact, status, created_at
            FROM observatory_suggestions
            ORDER BY created_at DESC LIMIT %(lim)s
        """, {"lim": limit})
    except Exception:
        return pd.DataFrame()
