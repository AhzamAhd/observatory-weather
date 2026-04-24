import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

SHEET_ID = os.environ.get(
    "SHEET_ID",
    "1TLRSueeZUUz4aoc4-1yjcTqzQywjyebMI5nhG9RHirQ"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    key_json = os.environ.get("GOOGLE_SHEETS_KEY")
    if key_json:
        info = json.loads(key_json)
        creds = Credentials.from_service_account_info(
            info, scopes=SCOPES)
    else:
        # Try streamlit secrets
        try:
            import streamlit as st
            info  = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(
                info, scopes=SCOPES)
        except Exception:
            print("  [ERROR] No Google credentials found.")
            return None

    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).sheet1
    return sheet

def load_subscriptions():
    sheet = get_sheet()
    if sheet is None:
        return []
    try:
        records = sheet.get_all_records()
        return records
    except Exception as e:
        print(f"  [ERROR] Could not load subscriptions: {e}")
        return []

def add_subscription(email, observatory,
                     threshold=80, alert_type="above"):
    sheet = get_sheet()
    if sheet is None:
        return False, "Could not connect to Google Sheets."

    try:
        # Check for duplicate
        records = sheet.get_all_records()
        for row in records:
            if (row["email"] == email and
                    row["observatory"] == observatory):
                return False, "Already subscribed to this observatory."

        # Add new row
        sheet.append_row([
            email,
            observatory,
            threshold,
            alert_type,
            "TRUE",
            datetime.utcnow().isoformat(),
            ""
        ])
        return True, "Subscribed successfully!"

    except Exception as e:
        return False, f"Error: {e}"

def remove_subscription(email, observatory):
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if (row["email"] == email and
                    row["observatory"] == observatory):
                # Row 1 is headers so data starts at row 2
                sheet.delete_rows(i + 2)
                return True
        return False
    except Exception as e:
        print(f"  [ERROR] Could not remove subscription: {e}")
        return False

def update_last_alerted(email, observatory):
    sheet = get_sheet()
    if sheet is None:
        return

    try:
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if (row["email"] == email and
                    row["observatory"] == observatory):
                # Column G is last_alerted (column 7)
                sheet.update_cell(
                    i + 2, 7,
                    datetime.utcnow().isoformat()
                )
                return
    except Exception as e:
        print(f"  [ERROR] Could not update last alerted: {e}")

if __name__ == "__main__":
    print("\n Testing Google Sheets connection...\n")
    sheet = get_sheet()
    if sheet:
        print("  Connected successfully!")
        subs = load_subscriptions()
        print(f"  Found {len(subs)} subscriptions")
    else:
        print("  Connection failed.")