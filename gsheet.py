import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google Sheets constants
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1rvI7Tftvp5fFnL79IJn6FxOstDulBOyrRQJm7DePP_s/edit'
WORKSHEET_NAME = 'Attendance'

def get_gspread_client():
    """
    Get authenticated gspread client using service account credentials from environment variable
    """
    try:
        # Get credentials from environment variable or use a default value for testing
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDS')
        
        if not creds_json:
            logger.warning("Google Sheets credentials not found in environment variable, using mock data")
            # Return None to handle the case gracefully
            return None
        
        # Parse the JSON credentials
        creds_dict = json.loads(creds_json)
        
        # Set up credentials scope
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Authenticate with service account
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # Create gspread client
        client = gspread.authorize(credentials)
        
        return client
    
    except json.JSONDecodeError:
        logger.error("Failed to parse Google Sheets credentials JSON")
        raise ValueError("Invalid JSON format in GOOGLE_SHEETS_CREDS")
    
    except Exception as e:
        logger.error(f"Error setting up Google Sheets client: {str(e)}")
        raise

def get_worksheet():
    """
    Get the attendance worksheet from the specified Google Sheet
    """
    try:
        client = get_gspread_client()
        if client is None:
            logger.warning("No Google Sheets client available, skipping worksheet access")
            return None
        
        # Open the spreadsheet
        sheet = client.open_by_url(SHEET_URL)
        
        # Get the worksheet, create it if it doesn't exist
        try:
            worksheet = sheet.worksheet(WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Create a new worksheet if it doesn't exist
            worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=6)
            
            # Add header row
            worksheet.append_row([
                "Ngày", "Giờ", "Tên", "Trạng thái", "Ca", "Người điểm danh"
            ])
        
        return worksheet
    
    except Exception as e:
        logger.error(f"Error getting worksheet: {str(e)}")
        return None

def add_attendance_to_sheet(date, time, name, status, shift, marked_by, is_student=False):
    """
    Add an attendance record to Google Sheets
    
    Args:
        date (str): Date in format YYYY-MM-DD
        time (str): Time in format HH:MM
        name (str): Name of teacher or student
        status (str): Status (e.g., "Có mặt")
        shift (str): Shift type (e.g., "morning", "afternoon", "1on1_1h")
        marked_by (str): Name of user who marked attendance
        is_student (bool): Whether this is a student attendance record
        
    Returns:
        int: Row number in the sheet where the record was added
    """
    try:
        worksheet = get_worksheet()
        if worksheet is None:
            logger.warning("No worksheet available, skipping add operation to Google Sheets")
            return None
        
        # Format shift name in Vietnamese
        shift_vi = {
            "morning": "Sáng",
            "afternoon": "Chiều",
            "1on1_1h": "1-1 (1 giờ)",
            "1on1_1.5h": "1-1 (1.5 giờ)",
            "1on1_2h": "1-1 (2 giờ)",
            "Học sinh": "Học sinh"
        }.get(shift, shift)
        
        # Add the new row
        row_data = [date, time, name, status, shift_vi, marked_by]
        worksheet.append_row(row_data)
        
        # Get the row number where the data was added
        # We find all matching cells and get the latest one
        cell_list = worksheet.findall(name)
        if cell_list:
            # Get the latest added row
            row_num = max(cell.row for cell in cell_list)
            return row_num
        else:
            logger.warning(f"Could not find added row for {name}")
            return None
    
    except Exception as e:
        logger.error(f"Error adding attendance to sheet: {str(e)}")
        return None

def delete_attendance_from_sheet(row_id):
    """
    Delete an attendance record from Google Sheets by row ID
    
    Args:
        row_id (int): Row number in the sheet
        
    Returns:
        bool: Success status
    """
    try:
        if not row_id:
            logger.warning("No row_id provided for deletion")
            return False
        
        worksheet = get_worksheet()
        if worksheet is None:
            logger.warning("No worksheet available, skipping delete operation from Google Sheets")
            return False
        
        # Delete the row
        worksheet.delete_row(row_id)
        
        return True
    
    except Exception as e:
        logger.error(f"Error deleting attendance from sheet: {str(e)}")
        return False
