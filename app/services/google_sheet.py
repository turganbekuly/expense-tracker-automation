import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Sheet1")
sheet_name_for_codes = os.getenv("GOOGLE_SHEET_NAME_FOR_CODES", "Codes")

if credentials_path is None:
    raise ValueError("GOOGLE_SHEETS_CREDENTIALS_PATH is not set. Please check .env file.")

# Set up Google Sheets API authorization
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
client = gspread.authorize(credentials)

def get_all_activation_codes():
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name_for_codes)
        records = sheet.get_all_records()  # Fetches all rows as dictionaries
        return [{"code": r["Codes:"]} for r in records if "Codes:" in r]  

def get_activation_code():
    # Open the sheet by ID and access the first tab
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    codes = sheet.get_all_records()

    for row_num, code in enumerate(codes, start=2):  # Row 2 onward to skip headers
        # Check if "Owner:" is empty for this row, meaning the code is unused
        if not code.get("Owner:"):
            return code.get("Codes:"), row_num  # Return the unused code and its row number

    return None, None

def update_owner_device_receipt(row_num, owner, device, receipt_number):
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    if owner:
        sheet.update_cell(row_num, 2, owner)  # Column 2 is "Owner:"
    if device:
        sheet.update_cell(row_num, 3, device)  # Column 3 is "Device:"
    if receipt_number:
        sheet.update_cell(row_num, 4, receipt_number)

def is_receipt_number_unique(receipt_number):
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    receipt_numbers = sheet.col_values(4)  # Assuming "Receipt Number:" is in Column D (index 4)
    
    # Check if the receipt number already exists in the column
    return receipt_number not in receipt_numbers[1:]  # Skip the header row

def confirm_row_availability(row_num):
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    # Check if the "Owner:" field in the specified row is still empty
    return not sheet.cell(row_num, 2).value  # Column 2 is "Owner:"

def append_activation_code_row(activation_code, phone_number, device, receipt_number):
        # Open the Google Sheet and append a new row with the activation details
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        new_row = [activation_code, phone_number, device, receipt_number]
        sheet.append_row(new_row)  # Appends the new row at the end of the sheet
        print(f"Appended to Google Sheets: {new_row}")
