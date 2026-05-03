import os
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

# ── Module-level connection pool ──────────────────────────────────
_pool = None

def _get_credentials():
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

    return host, user, password, port

def get_pool():
    global _pool
    if _pool is None:
        host, user, password, port = _get_credentials()
        if not host or not password:
            raise ValueError(
                "Database credentials not found.")
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn  = 2,
            maxconn  = 10,
            host     = host,
            port     = port,
            database = "postgres",
            user     = user,
            password = password,
            sslmode  = "require",
            connect_timeout = 10,
            keepalives = 1,
            keepalives_idle = 30,
            keepalives_interval = 10,
            keepalives_count = 5
        )
    return _pool

def get_connection():
    return get_pool().getconn()

def release_connection(conn):
    try:
        get_pool().putconn(conn)
    except Exception:
        pass

def _convert_decimals(df):
    for col in df.columns:
        if len(df) > 0:
            sample = df[col].dropna()
            if (len(sample) > 0 and
                    isinstance(sample.iloc[0], Decimal)):
                df[col] = df[col].astype(float)
    return df

def query_df(sql, params=None):
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
        return _convert_decimals(df)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)

def execute(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)

def execute_many(sql, rows):
    conn = get_connection()
    try:
        cur = conn.cursor()
        psycopg2.extras.execute_values(cur, sql, rows)
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)

def fetch_one(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)

def fetch_all(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_connection(conn)


if __name__ == "__main__":
    import time
    print("\n  Testing connection pool...\n")

    start = time.time()
    df    = query_df(
        "SELECT COUNT(*) AS count FROM observatories")
    print(
        f"  First query:  {time.time()-start:.2f}s "
        f"— {df.iloc[0]['count']} observatories"
    )

    start = time.time()
    df    = query_df(
        "SELECT COUNT(*) AS count FROM weather_readings")
    print(
        f"  Second query: {time.time()-start:.2f}s "
        f"— {df.iloc[0]['count']} readings"
    )

    start = time.time()
    df    = query_df(
        "SELECT COUNT(*) AS count FROM weather_readings")
    print(
        f"  Third query:  {time.time()-start:.2f}s "
        f"(should be faster)\n"
    )