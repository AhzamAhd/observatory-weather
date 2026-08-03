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

def release_connection(conn, close=False):
    try:
        get_pool().putconn(conn, close=close)
    except Exception:
        pass

# Errors that mean the pooled connection is dead (Supabase closed it
# server-side on idle timeout, or the SSL link dropped). The connection
# must be discarded, not returned to the pool, and the query retried.
_CONN_DEAD_ERRORS = (
    psycopg2.OperationalError,
    psycopg2.InterfaceError,
)

def _is_dead_connection(conn, exc):
    if isinstance(exc, _CONN_DEAD_ERRORS):
        return True
    # closed != 0 means the connection is no longer usable.
    return getattr(conn, "closed", 0) != 0

def _convert_decimals(df):
    for col in df.columns:
        if len(df) > 0:
            sample = df[col].dropna()
            if (len(sample) > 0 and
                    isinstance(sample.iloc[0], Decimal)):
                df[col] = df[col].astype(float)
    return df

def _run(work):
    """Borrow a connection, run `work(conn)`, and return its result.

    If the borrowed connection turns out to be dead (Supabase closed it
    on idle timeout, or the SSL link dropped), it is discarded from the
    pool and the operation is retried once on a fresh connection.
    """
    last_exc = None
    for attempt in range(2):
        conn = get_connection()
        dead = False
        try:
            return work(conn)
        except Exception as e:
            last_exc = e
            dead = _is_dead_connection(conn, e)
            if not dead:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
        finally:
            release_connection(conn, close=dead)
        # We only reach here after a dead connection on the first
        # attempt; loop once more with a fresh one.
    raise last_exc

def query_df(sql, params=None):
    def work(conn):
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        return _convert_decimals(df)
    return _run(work)

def execute(sql, params=None):
    def work(conn):
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
    return _run(work)

def execute_many(sql, rows):
    def work(conn):
        cur = conn.cursor()
        psycopg2.extras.execute_values(cur, sql, rows)
        conn.commit()
        cur.close()
    return _run(work)

def fetch_one(sql, params=None):
    def work(conn):
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    return _run(work)

def fetch_all(sql, params=None):
    def work(conn):
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    return _run(work)


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