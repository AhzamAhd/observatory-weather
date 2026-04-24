import smtplib
import json
import os
import sqlite3
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Config ────────────────────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("ALERT_EMAIL", "")
SENDER_PASSWORD = os.environ.get("ALERT_PASSWORD", "")
SUBSCRIPTIONS_FILE = "subscriptions.json"

# ── Load subscriptions ────────────────────────────────────────────
def load_subscriptions():
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        return []
    with open(SUBSCRIPTIONS_FILE, "r") as f:
        return json.load(f)

def save_subscriptions(subs):
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(subs, f, indent=2)

def add_subscription(email, observatory,
                     threshold=80, alert_type="above"):
    subs = load_subscriptions()

    # Check for duplicate
    for sub in subs:
        if (sub["email"] == email and
                sub["observatory"] == observatory):
            return False, "Already subscribed to this observatory."

    subs.append({
        "email":       email,
        "observatory": observatory,
        "threshold":   threshold,
        "alert_type":  alert_type,
        "active":      True,
        "created_at":  datetime.utcnow().isoformat(),
        "last_alerted": None
    })
    save_subscriptions(subs)
    return True, "Subscribed successfully!"

def remove_subscription(email, observatory):
    subs    = load_subscriptions()
    new_subs = [
        s for s in subs
        if not (s["email"] == email and
                s["observatory"] == observatory)
    ]
    save_subscriptions(new_subs)
    return len(subs) - len(new_subs) > 0

# ── Get current scores ────────────────────────────────────────────
def get_current_scores():
    conn = sqlite3.connect(
        "data/silver/observatory_weather.db")
    df   = pd.read_sql("""
        SELECT
            o.name          AS observatory,
            o.country,
            o.altitude_m,
            w.fetch_date,
            w.fetch_time,
            w.cloud_cover_pct,
            w.humidity_pct,
            w.wind_speed_ms,
            w.temperature_c,
            ROUND(MAX(0,
                100
                - (w.cloud_cover_pct * 0.50)
                - (CASE WHEN w.humidity_pct > 85
                   THEN (w.humidity_pct - 85) * 2.0 ELSE 0 END)
                - (CASE WHEN w.wind_speed_ms > 15
                   THEN (w.wind_speed_ms - 15) * 2.0 ELSE 0 END)
            ), 1) AS score
        FROM weather_readings w
        JOIN observatories o ON w.observatory_id = o.id
        ORDER BY o.name
    """, conn)
    conn.close()
    return df

# ── Build email ───────────────────────────────────────────────────
def build_email_html(observatory, score,
                     threshold, alert_type,
                     weather_data):
    if score >= 80:
        condition = "Excellent"
        color     = "#1D9E75"
        emoji     = "🟢"
    elif score >= 60:
        condition = "Good"
        color     = "#378ADD"
        emoji     = "🔵"
    elif score >= 40:
        condition = "Marginal"
        color     = "#EF9F27"
        emoji     = "🟡"
    else:
        condition = "Poor"
        color     = "#E24B4A"
        emoji     = "🔴"

    if alert_type == "above":
        subject_line = (
            f"✅ {observatory} is now Excellent "
            f"— Score {score}/100")
        headline = (
            f"Good news! {observatory} has reached "
            f"your threshold of {threshold}/100")
    else:
        subject_line = (
            f"⚠️ {observatory} conditions dropping "
            f"— Score {score}/100")
        headline = (
            f"Alert: {observatory} has dropped below "
            f"your threshold of {threshold}/100")

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;
                 background: #0E1117; color: #FAFAFA;
                 padding: 20px; margin: 0;">

      <div style="max-width: 600px; margin: 0 auto;
                  background: #1A1D24;
                  border-radius: 12px; overflow: hidden;">

        <!-- Header -->
        <div style="background: {color};
                    padding: 24px; text-align: center;">
          <h1 style="margin: 0; color: white; font-size: 24px;">
            🔭 Observatory Weather Alert
          </h1>
          <p style="margin: 8px 0 0; color: white;
                    opacity: 0.9; font-size: 14px;">
            Global Observatory Weather Tracker
          </p>
        </div>

        <!-- Main content -->
        <div style="padding: 24px;">
          <h2 style="color: {color}; margin-top: 0;">
            {headline}
          </h2>

          <!-- Score card -->
          <div style="background: {color}22;
                      border: 1px solid {color};
                      border-radius: 8px;
                      padding: 16px;
                      text-align: center;
                      margin: 16px 0;">
            <div style="font-size: 48px; font-weight: bold;
                        color: {color};">
              {score}/100
            </div>
            <div style="font-size: 18px; color: {color};">
              {emoji} {condition}
            </div>
            <div style="font-size: 14px;
                        color: #888; margin-top: 4px;">
              {observatory}
            </div>
          </div>

          <!-- Weather details -->
          <h3 style="color: #FAFAFA;">
            Current conditions
          </h3>
          <table style="width: 100%;
                        border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #333;">
              <td style="padding: 8px; color: #888;">
                ☁️ Cloud Cover
              </td>
              <td style="padding: 8px; font-weight: bold;
                         text-align: right;">
                {weather_data.get('cloud_cover_pct', 'N/A')}%
              </td>
            </tr>
            <tr style="border-bottom: 1px solid #333;">
              <td style="padding: 8px; color: #888;">
                💧 Humidity
              </td>
              <td style="padding: 8px; font-weight: bold;
                         text-align: right;">
                {weather_data.get('humidity_pct', 'N/A')}%
              </td>
            </tr>
            <tr style="border-bottom: 1px solid #333;">
              <td style="padding: 8px; color: #888;">
                💨 Wind Speed
              </td>
              <td style="padding: 8px; font-weight: bold;
                         text-align: right;">
                {weather_data.get('wind_speed_ms', 'N/A')} m/s
              </td>
            </tr>
            <tr>
              <td style="padding: 8px; color: #888;">
                🌡️ Temperature
              </td>
              <td style="padding: 8px; font-weight: bold;
                         text-align: right;">
                {weather_data.get('temperature_c', 'N/A')}°C
              </td>
            </tr>
          </table>

          <!-- Timestamp -->
          <p style="color: #888; font-size: 12px;
                    margin-top: 16px;">
            Data fetched: {weather_data.get('fetch_time', '')}
            UTC on {weather_data.get('fetch_date', '')}
          </p>

          <!-- Tips -->
          <div style="background: #333;
                      border-radius: 8px;
                      padding: 12px;
                      margin-top: 16px;">
            <p style="margin: 0; font-size: 13px;
                      color: #ccc;">
              💡 <b>Observing tip:</b>
              {"Tonight looks excellent. Open the dome and enjoy — especially good for faint deep sky objects and galaxies." if score >= 80 else "Conditions are marginal tonight. Stick to bright targets like planets, the Moon, and double stars." if score >= 40 else "Conditions are poor tonight. A good night for planning your next session or reviewing previous data."}
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div style="background: #111;
                    padding: 16px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;">
          <p style="margin: 0;">
            You are receiving this because you subscribed
            to alerts for <b>{observatory}</b>
            with a threshold of {threshold}/100.
          </p>
          <p style="margin: 8px 0 0;">
            Global Observatory Weather Tracker ·
            Data from Open-Meteo ·
            {datetime.utcnow().strftime('%Y-%m-%d')} UTC
          </p>
        </div>

      </div>
    </body>
    </html>
    """
    return subject_line, html

# ── Send email ────────────────────────────────────────────────────
def send_email(to_email, subject, html_body):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("  [SKIP] No email credentials configured.")
        return False

    msg                    = MIMEMultipart("alternative")
    msg["Subject"]         = subject
    msg["From"]            = (
        f"Observatory Weather Tracker <{SENDER_EMAIL}>")
    msg["To"]              = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465
        ) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(
                SENDER_EMAIL, to_email, msg.as_string())
        print(f"  ✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send to {to_email}: {e}")
        return False

# ── Main alert checker ────────────────────────────────────────────
def run_alert_checker():
    print(
        f"\n Running alert checker — "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
    )

    subs   = load_subscriptions()
    scores = get_current_scores()

    if not subs:
        print("  No subscriptions found.")
        return

    if scores.empty:
        print("  No score data found.")
        return

    print(f"  Checking {len(subs)} subscriptions...\n")

    alerts_sent = 0
    for i, sub in enumerate(subs):
        if not sub.get("active", True):
            continue

        obs_row = scores[
            scores["observatory"] == sub["observatory"]]
        if obs_row.empty:
            print(
                f"  [SKIP] {sub['observatory']} "
                f"not found in database")
            continue

        row       = obs_row.iloc[0]
        score     = row["score"]
        threshold = sub.get("threshold", 80)
        alert_type = sub.get("alert_type", "above")

        should_alert = (
            (alert_type == "above" and score >= threshold) or
            (alert_type == "below" and score < threshold)
        )

        print(
            f"  {sub['email'][:30]:<32} "
            f"{sub['observatory'][:30]:<32} "
            f"Score: {score:>5} "
            f"Threshold: {threshold:>3} "
            f"Alert: {'YES' if should_alert else 'no'}"
        )

        if should_alert:
            weather_data = {
                "cloud_cover_pct": row["cloud_cover_pct"],
                "humidity_pct":    row["humidity_pct"],
                "wind_speed_ms":   row["wind_speed_ms"],
                "temperature_c":   row["temperature_c"],
                "fetch_date":      row["fetch_date"],
                "fetch_time":      row["fetch_time"]
            }
            subject, html = build_email_html(
                sub["observatory"], score,
                threshold, alert_type, weather_data
            )
            sent = send_email(
                sub["email"], subject, html)
            if sent:
                subs[i]["last_alerted"] = (
                    datetime.utcnow().isoformat())
                alerts_sent += 1

    save_subscriptions(subs)
    print(
        f"\n  Done. {alerts_sent} alerts sent.\n")

if __name__ == "__main__":
    run_alert_checker()