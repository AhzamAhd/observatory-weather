from db import get_connection, release_connection, query_df, fetch_one
from datetime import datetime

def _ensure_object_column():
    """Add the optional object_name column if it doesn't exist yet."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("ALTER TABLE subscriptions "
                    "ADD COLUMN IF NOT EXISTS object_name TEXT")
        conn.commit()
        cur.close()
        release_connection(conn)
    except Exception:
        pass

def load_subscriptions():
    _ensure_object_column()
    df = query_df("""
        SELECT email, observatory, object_name, threshold,
               alert_type, active, created_at, last_alerted
        FROM subscriptions
        WHERE active = TRUE
    """)
    if df.empty:
        return []
    return df.to_dict("records")

def add_subscription(email, observatory,
                     threshold=80, alert_type="above",
                     object_name=None):
    try:
        _ensure_object_column()
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO subscriptions
                (email, observatory, object_name, threshold,
                 alert_type, active, created_at)
            VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            ON CONFLICT (email, observatory)
            DO UPDATE SET
                object_name = EXCLUDED.object_name,
                threshold   = EXCLUDED.threshold,
                alert_type  = EXCLUDED.alert_type,
                active      = TRUE
            RETURNING id
        """, (email, observatory, object_name or None,
              threshold, alert_type))
        conn.commit()
        cur.close()
        release_connection(conn)
        return True, "Subscribed successfully!"
    except Exception as e:
        return False, f"Error: {e}"

def remove_subscription(email, observatory):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            DELETE FROM subscriptions
            WHERE email = %s AND observatory = %s
        """, (email, observatory))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        release_connection(conn)
        return deleted > 0
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def update_last_alerted(email, observatory):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            UPDATE subscriptions
            SET last_alerted = NOW()
            WHERE email = %s AND observatory = %s
        """, (email, observatory))
        conn.commit()
        cur.close()
        release_connection(conn)
    except Exception as e:
        print(f"  [ERROR] {e}")

if __name__ == "__main__":
    print("\n  Testing subscriptions...\n")
    subs = load_subscriptions()
    print(f"  Found {len(subs)} active subscriptions\n")