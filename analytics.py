"""
Self-owned visit tracking.

Records one row in page_visits per Streamlit session so GOWC keeps its
own visitor count independent of Google Analytics. Every helper is
best-effort: analytics must never take the app down, so DB errors are
swallowed and logging returns quietly.
"""
import uuid
import streamlit as st
import db


def log_visit(user_id=None, page=None):
    """Record this session as a visit exactly once.

    Uses a per-session flag so a single browser session counts as one
    visit no matter how many times the script reruns. Safe to call on
    every run; only the first call per session writes a row.
    """
    if st.session_state.get("_visit_logged"):
        return
    # Mark first so a failure here still won't retry every rerun.
    st.session_state["_visit_logged"] = True

    session_id = st.session_state.get("_visit_session_id")
    if not session_id:
        session_id = uuid.uuid4().hex
        st.session_state["_visit_session_id"] = session_id

    try:
        db.execute(
            "INSERT INTO page_visits (session_id, user_id, page) "
            "VALUES (%s, %s, %s)",
            (session_id, user_id, page),
        )
    except Exception:
        # Never let analytics break the page.
        pass


def get_visit_stats():
    """Return headline visit counts. Empty dict on any error."""
    try:
        row = db.fetch_one(
            """
            SELECT
                COUNT(*)                          AS total_visits,
                COUNT(DISTINCT session_id)        AS unique_sessions,
                COUNT(*) FILTER (
                    WHERE visited_at >= NOW() - INTERVAL '7 days'
                )                                 AS visits_7d,
                COUNT(*) FILTER (
                    WHERE visited_at >= NOW() - INTERVAL '24 hours'
                )                                 AS visits_24h,
                MIN(visited_at)                   AS first_visit
            FROM page_visits
            """
        )
        return row or {}
    except Exception:
        return {}


def get_daily_visits(days=30):
    """Return a list of {day, visits, unique_sessions} for the last N days."""
    try:
        return db.fetch_all(
            """
            SELECT
                DATE(visited_at)            AS day,
                COUNT(*)                    AS visits,
                COUNT(DISTINCT session_id)  AS unique_sessions
            FROM page_visits
            WHERE visited_at >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY DATE(visited_at)
            ORDER BY day
            """,
            (days,),
        )
    except Exception:
        return []
