import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

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