from db import get_connection, query_df, fetch_one
from datetime import datetime

def load_subscriptions():
    df = query_df("""
        SELECT email, observatory, threshold,
               alert_type, active, created_at, last_alerted
        FROM subscriptions
        WHERE active = TRUE
    """)
    if df.empty:
        return []
    return df.to_dict("records")

def add_subscription(email, observatory,
                     threshold=80, alert_type="above"):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO subscriptions
                (email, observatory, threshold,
                 alert_type, active, created_at)
            VALUES (%s, %s, %s, %s, TRUE, NOW())
            ON CONFLICT (email, observatory)
            DO UPDATE SET
                threshold  = EXCLUDED.threshold,
                alert_type = EXCLUDED.alert_type,
                active     = TRUE
            RETURNING id
        """, (email, observatory, threshold, alert_type))
        conn.commit()
        cur.close()
        conn.close()
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
        conn.close()
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
        conn.close()
    except Exception as e:
        print(f"  [ERROR] {e}")

if __name__ == "__main__":
    print("\n  Testing subscriptions...\n")
    subs = load_subscriptions()
    print(f"  Found {len(subs)} active subscriptions\n")