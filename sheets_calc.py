import os
import json
import time
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_gc():
    """
    Render-safe Google Sheets auth.
    Expects service account JSON stored in env var GOOGLE_CREDENTIALS_JSON.
    """
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise RuntimeError("Missing GOOGLE_CREDENTIALS_JSON environment variable")

    try:
        info = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GOOGLE_CREDENTIALS_JSON is not valid JSON: {e}")

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def calculate_cost(spreadsheet_id: str, dashboard_tab: str, inputs: dict) -> str:
    gc = get_gc()
    sh = gc.open_by_key(spreadsheet_id)
    sheet = sh.worksheet(dashboard_tab)

    updates = [
        {"range": "C4",  "values": [[inputs["material"]]]},
        {"range": "C5",  "values": [[inputs["thickness"]]]},
        {"range": "C6",  "values": [[inputs["area_sqft"]]]},
        {"range": "C7",  "values": [[inputs["gas"]]]},
        {"range": "C8",  "values": [[inputs["cut_len"]]]},
        {"range": "C10", "values": [[inputs["bends"]]]},
        {"range": "C12", "values": [[inputs["number_of_pieces"]]]},
        {"range": "C13", "values": [[inputs["fab_hours"]]]},
        {"range": "C14", "values": [[inputs["pro_hours"]]]},
    ]

    sheet.batch_update(updates, value_input_option="USER_ENTERED")

    # Give Sheets a moment to recalculate formulas
    time.sleep(2)

    return sheet.acell("C31").value or "0"
