import gspread
import time
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gc():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
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
    time.sleep(2)

    return sheet.acell("C31").value or "0"
