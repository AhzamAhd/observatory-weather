import pandas as pd
from datetime import datetime
from db import execute, query_df


def ensure_feedback_table():
    """Create the feedback table if it doesn't exist yet."""
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id          SERIAL PRIMARY KEY,
                category    TEXT,
                message     TEXT NOT NULL,
                contact     TEXT,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        return True
    except Exception:
        return False


def add_feedback(category, message, contact=""):
    """Store a single feedback/suggestion submission."""
    try:
        ensure_feedback_table()
        execute("""
            INSERT INTO feedback (category, message, contact, created_at)
            VALUES (%s, %s, %s, %s)
        """, [category, message, contact, datetime.utcnow()])
        return True, "Thanks! Your feedback has been recorded."
    except Exception as e:
        return False, f"Could not save feedback: {e}"


def get_feedback(limit=100):
    """Return recent feedback (for the site owner)."""
    try:
        ensure_feedback_table()
        return query_df("""
            SELECT category, message, contact, created_at
            FROM feedback
            ORDER BY created_at DESC
            LIMIT %(lim)s
        """, {"lim": limit})
    except Exception:
        return pd.DataFrame()
