import smartsheet
from datetime import datetime, timedelta

# Configuration
SMARTSHEET_TOKEN='j4fc01RK42GEZuxlRP49zCBYnlwMr3HwjYXsz'
SMARTSHEET_ID='5CRwhFxhPX7pfvcQ6PVRx7VX8ggpW7JPfh4xfHx1'

def get_week_range(date):
    """
    Get the start (Monday) and end (Sunday) of the week for a given date
    """
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end

def validate_credentials(access_token, sheet_id):
    """
    Validate Smartsheet credentials before proceeding
    """
    try:
        print("Validating Smartsheet credentials...")
        smartsheet_client = smartsheet.Smartsheet(access_token)
        smartsheet_client.errors_as_exceptions(True)
        
        # Try to get current user info to validate token
        current_user = smartsheet_client.Users.get_current_user()
        print(f"✓ Access token valid - Authenticated as: {current_user.email}")
        
        # Try to access the sheet to validate sheet ID
        sheet = smartsheet_client.Sheets.get_sheet(sheet_id)
        print(f"✓ Sheet ID valid - Sheet name: {sheet.name}")
        print(f"✓ Sheet has {sheet.total_row_count} rows and {len(sheet.columns)} columns")
        
        return True
        
    except smartsheet.exceptions.ApiError as e:
        if e.error.result.status_code == 401:
            print("✗ Authentication failed - Invalid access token")
        elif e.error.result.status_code == 404:
            print("✗ Sheet not found - Invalid sheet ID or no access")
        else:
            print(f"✗ API Error: {e.error.result.message}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False

def get_smartsheet_releases(access_token, sheet_id):
    """
    Fetch release version, start date, and end date from Smartsheet
    Filter for current week and next week only
    """
    # Initialize Smartsheet client
    smartsheet_client = smartsheet.Smartsheet(access_token)
    smartsheet_client.errors_as_exceptions(True)
    
    # Get the sheet
    sheet = smartsheet_client.Sheets.get_sheet(sheet_id)
    
    # Extract column names and find target columns
    columns = {col.id: col.title for col in sheet.columns}
    column_ids = {title.lower(): col_id for col_id, title in columns.items()}
    
    # Debug: Print all column names
    print("\n📋 Available columns in sheet:")
    for col_id, col_title in columns.items():
        print(f"   - Column Name : {col_title} ")
    print()

    # Get current date and week ranges
    today = datetime.now().date()
    current_week_start, current_week_end = get_week_range(today)
    next_week_start = current_week_start + timedelta(days=7)
    next_week_end = current_week_end + timedelta(days=7)

    print(f"Today: {today}")
    print(f"Current Week: {current_week_start} to {current_week_end}")
    print(f"Next Week: {next_week_start} to {next_week_end}")
    print("=" * 60)

    # Extract row data
    releases = []
    rows_processed = 0
    
    for row in sheet.rows:
        # Skip row if all cells are empty
        if all(
            (getattr(cell, "display_value", None) in [None, ""] and getattr(cell, "value", None) in [None, ""])
            for cell in row.cells
        ):
            continue

        rows_processed += 1
        row_data = {}
        for cell in row.cells:
            column_name = columns[cell.column_id].lower()
            print(f"  {column_name}: {getattr(cell, 'display_value', None)} | {getattr(cell, 'value', None)}")

            # Look for release version, start date, and end date columns
            if 'release' in column_name or 'version' in column_name:
                row_data['release_version'] = cell.display_value if cell.display_value else cell.value
                row_data['release_column'] = columns[cell.column_id]
            elif 'start' in column_name and 'date' in column_name:
                row_data['start_date'] = cell.value
                row_data['start_column'] = columns[cell.column_id]
            elif 'end' in column_name and 'date' in column_name:
                row_data['end_date'] = cell.value
                row_data['end_column'] = columns[cell.column_id]

        # Only process rows that have all required fields
        if all(key in row_data for key in ['release_version', 'start_date', 'end_date']):
            try:
                # Parse dates - handle different date formats
                if isinstance(row_data['start_date'], str):
                    # Try different date formats
                    for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            start_date = datetime.strptime(row_data['start_date'], date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        print(f"⚠️  Could not parse start_date: {row_data['start_date']}")
                        continue
                else:
                    start_date = row_data['start_date']
                
                if isinstance(row_data['end_date'], str):
                    for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            end_date = datetime.strptime(row_data['end_date'], date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        print(f"⚠️  Could not parse end_date: {row_data['end_date']}")
                        continue
                else:
                    end_date = row_data['end_date']
                
                # Check if the release falls in current week or next week
                if (current_week_start <= start_date <= next_week_end) or \
                   (current_week_start <= end_date <= next_week_end) or \
                   (start_date <= current_week_start and end_date >= next_week_end):
                    releases.append({
                        'release_version': row_data['release_version'],
                        'start_date': start_date,
                        'end_date': end_date
                    })
                    print(f"✓ Matched release: {row_data['release_version']}")
            except (ValueError, TypeError) as e:
                # Skip rows with invalid dates
                print(f"⚠️  Error processing row: {e}")
                continue
    
    print(f"\n📊 Processed {rows_processed} rows total")
    return releases

def main():
    """
    Main function to fetch and display releases for current and next week
    """
    try:
        # Validate credentials first
        if not validate_credentials(SMARTSHEET_TOKEN, SMARTSHEET_ID):
            print("\n❌ Credential validation failed. Please check your access token and sheet ID.")
            return
        
        print("\n" + "=" * 60)
        print("Fetching releases from Smartsheet...\n")
        releases = get_smartsheet_releases(SMARTSHEET_TOKEN, SMARTSHEET_ID)
        
        if not releases:
            print("No releases found for current week or next week.")
        else:
            print(f"\nFound {len(releases)} release(s) for current and next week:\n")
            for i, release in enumerate(releases, 1):
                print(f"{i}. Release Version: {release['release_version']}")
                print(f"   Start Date: {release['start_date']}")
                print(f"   End Date: {release['end_date']}")
                print("-" * 60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()