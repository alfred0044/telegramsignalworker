import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import base64
import json
import os


# Setup
print("GOOGLE_CREDENTIALS_B64 found:", os.getenv("GOOGLE_CREDENTIALS_B64") is not None)

# Decode and load credentials
cred_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if cred_b64:
    cred_json = base64.b64decode(cred_b64).decode("utf-8")
    credentials_dict = json.loads(cred_json)
else:
    raise Exception("Missing GOOGLE_CREDENTIALS_B64 in .env")

from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)

client = gspread.authorize(credentials)

# Open spreadsheet and worksheet
sheet = client.open("XAUUSD Signal Tracker").worksheet("Signals")

def log_signal(signal_text, source_id, status="Sent"):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    row = [timestamp, signal_text, str(source_id), "MT4 Copier", status]
    sheet.append_row(row)

def update_status(signal_text, new_status):
    try:
        cell = sheet.find(signal_text)
        sheet.update_cell(cell.row, 5, new_status)
        print(f"✅ Status updated to '{new_status}' for row {cell.row}")
    except Exception as e:
        print(f"⚠️ Could not update status: {e}")