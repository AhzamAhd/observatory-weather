import os
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Connection helpers ────────────────────────────────────────────
def get_connection():
    host     = os.environ.get("SUPABASE_DB_HOST")
    user     = os.environ.get(
        "SUPABASE_DB_USER", "postgres")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    port     = int(os.environ.get(
        "SUPABASE_DB_PORT", 5432))

    if not host or not password:
        try:
            import streamlit as st
            host     = st.secrets.get("SUPABASE_DB_HOST")
            user     = st.secrets.get(
                "SUPABASE_DB_USER", "postgres")
            password = st.secrets.get(
                "SUPABASE_DB_PASSWORD")
            port     = int(st.secrets.get(
                "SUPABASE_DB_PORT", 5432))
        except Exception:
            pass

    if not host or not password:
        raise ValueError(
            "Database credentials not found.")

    return psycopg2.connect(
        host     = host,
        port     = port,
        database = "postgres",
        user     = user,
        password = password,
        sslmode  = "require"
    )

# ── Query helpers ─────────────────────────────────────────────────
def query_df(sql, params=None):
    """
    Execute a SELECT query and return a DataFrame.
    Auto-converts Decimal columns to float.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(r) for r in rows])

        # Convert Decimal columns to float
        from decimal import Decimal
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if column has Decimal values
                sample = df[col].dropna().head(1)
                if len(sample) > 0 and isinstance(
                    sample.iloc[0], Decimal
                ):
                    df[col] = df[col].astype(float)
        return df
    finally:
        conn.close()

def execute(sql, params=None):
    """
    Execute an INSERT/UPDATE/DELETE statement.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
    finally:
        conn.close()

def execute_many(sql, rows):
    """
    Execute a query with multiple rows efficiently.
    Used for bulk inserts.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        psycopg2.extras.execute_values(cur, sql, rows)
        conn.commit()
        cur.close()
    finally:
        conn.close()

def fetch_one(sql, params=None):
    """
    Execute a query and return one row as a dict.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    finally:
        conn.close()

def fetch_all(sql, params=None):
    """
    Execute a query and return all rows as a list of dicts.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n  Testing Supabase connection...\n")
    try:
        df = query_df(
            "SELECT COUNT(*) AS count "
            "FROM observatories"
        )
        print(f"  ✅ Connected!")
        print(f"  📊 {df.iloc[0]['count']} "
              f"observatories in database\n")
    except Exception as e:
        print(f"  ❌ Error: {e}\n")