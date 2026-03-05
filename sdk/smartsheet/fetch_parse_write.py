"""
Smartsheet sync functions - fetch releases and write to Google Sheets
Fetches from Smartsheet → Parses → Filters → Writes to Google Sheets (daily 8 AM)
"""

import os
import re
import json
from datetime import datetime, timedelta

import requests
import gspread
from dateutil.relativedelta import relativedelta
from slack_worker.config import config


def fetch_sheet_by_id(sheet_id, access_token):
    """Fetch sheet data by ID from Smartsheet API"""
    url = f"https://api.smartsheet.com/2.0/sheets/{sheet_id}?includeAll=true"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def extract_version(version_str):
    """Extract version from string like '4.12.30 in Fast Channel'"""
    version_pattern = r"\b(\d+\.\d+(?:\.\d+)?)\b"
    matches = re.findall(version_pattern, version_str)
    return matches[0] if matches else None


def shift_from_weekend(date, offset_days):
    """Takes a date and adds/subtracts days"""
    shifted_date = date + timedelta(days=offset_days)
    weekday = shifted_date.weekday()

    if weekday == 5:
        shifted_date = shifted_date + timedelta(days=2)
    elif weekday == 6:
        shifted_date = shifted_date + timedelta(days=1)

    return shifted_date


def get_release_filter_date_range():
    """Get date range for filtering releases.

    Calculates: current month start to (current month + N months end)
    where N is configurable via RELEASE_FILTER_MONTHS_AHEAD env var.

    Default: 1 month ahead from current month start
    Example: If today is Feb 26, 2026:
        - month_start: Feb 1, 2026
        - month_end: Mar 31, 2026 (1 month ahead)

    To modify range without code changes:
        RELEASE_FILTER_MONTHS_AHEAD=2  (extends to 2 months ahead)
        RELEASE_FILTER_MONTHS_AHEAD=3  (extends to 3 months ahead)

    Returns:
        tuple: (month_start, month_end) as date objects
    """
    current_date = datetime.now().date()
    months_ahead = int(os.getenv("RELEASE_FILTER_MONTHS_AHEAD", "1"))

    month_start = current_date.replace(day=1)
    # Add months_ahead + 1 to get end of the last month in range
    next_month = month_start + relativedelta(months=months_ahead + 1)
    month_end = next_month - timedelta(days=1)

    return month_start, month_end


def parse_sheet_releases(sheet, source_version):
    """Parse releases from a Smartsheet sheet"""
    releases = []
    rows = sheet.get("rows", [])

    for row in rows:
        cells = row.get("cells", [])

        if len(cells) >= 3:
            release_name = cells[0].get("displayValue") or cells[0].get("value", "")
            version_cell = cells[1].get("displayValue") or cells[1].get("value", "")
            date_cell = cells[2].get("value", "")
            flags = (
                cells[3].get("displayValue") or cells[3].get("value", "")
                if len(cells) > 3
                else ""
            )

            if not release_name or not date_cell:
                continue

            try:
                # Parse date
                date_str = date_cell.split("T")[0]
                finish_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                # Extract version from cell combined with release name
                version_str = extract_version(
                    str(version_cell) + " " + str(release_name)
                )

                if not version_str:
                    version_str = source_version

                releases.append(
                    {
                        "version": version_str,
                        "release_name": str(release_name),
                        "finish_date": finish_date,
                        "flag": str(flags),
                    }
                )
            except Exception:
                continue

    return releases


def filter_releases(all_releases):
    """Filter releases by z-stream format, dev flag, and date range.

    Note: Releases are already fetched from specific version Smartsheet IDs,
    so version range filtering is not needed here.

    Date range is configurable via RELEASE_FILTER_MONTHS_AHEAD env var (default: 1 month ahead).

    Only includes:
    - z-stream versions (x.y.z format) like 4.14.61, not just 4.14
    - releases with 'dev' flag
    - releases within configured date range
    """

    month_start, month_end = get_release_filter_date_range()

    filtered = []

    for release in all_releases:
        version_str = release["version"]
        finish_date = release["finish_date"]
        flag = release.get("flag", "")

        # Filter by z-stream format only (x.y.z, not x.y)
        # A z-stream version should have 3 parts when split by dot
        version_parts = version_str.split(".")
        if len(version_parts) < 3:
            continue

        # Filter by flag - only include "dev" flag
        if "dev" not in flag.lower():
            continue

        # Filter by date range
        if month_start <= finish_date <= month_end:
            filtered.append(release)

    # Sort by finish_date
    filtered.sort(key=lambda x: x["finish_date"])

    return filtered


def write_to_gsheet(filtered_releases, gsheet_creds):
    """Write filtered releases to Google Sheets ROTA -> Assignments

    Intelligently compares fetched releases with existing data:
    - Updates dates (B, C) for existing releases (preserves PM/QE1/QE2 in D-G)
    - Adds new rows for new releases
    - Marks rows for deleted releases (optional)

    This prevents mismatching PM/QE assignments to wrong releases.
    """

    try:
        creds_str = gsheet_creds.strip()
        if creds_str.startswith("'") and creds_str.endswith("'"):
            creds_str = creds_str[1:-1]

        creds_dict = json.loads(creds_str)
        client = gspread.service_account_from_dict(creds_dict)

        spreadsheet = client.open(config.ROTA_SHEET)

        try:
            worksheet = spreadsheet.worksheet(config.ASSIGNMENT_WSHEET)
        except gspread.exceptions.WorksheetNotFound:
            available = [ws.title for ws in spreadsheet.worksheets()]
            raise Exception(f"Assignments worksheet not found. Available: {available}")

    except (Exception, PermissionError) as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise Exception("ROTA spreadsheet not found")
        elif "403" in error_msg or "permission" in error_msg.lower():
            raise Exception("Permission denied for ROTA spreadsheet")
        else:
            raise

    # Get existing data from worksheet
    all_values = worksheet.get_all_values()

    if not all_values or len(all_values) == 0:
        # Worksheet is empty, write headers and all new releases
        worksheet.update(
            values=[["Release", "Start Date", "End Date"]], range_name="A1:C1"
        )
        all_values = [["Release", "Start Date", "End Date"]]

    # Build map of existing releases: {version: row_index}
    existing_releases = {}
    for idx in range(1, len(all_values)):  # Skip header (row 0)
        row = all_values[idx]
        if row and len(row) > 0 and row[0]:  # Has version in column A
            version = row[0]
            existing_releases[version] = idx

    # Build map of fetched releases with calculated dates
    fetched_releases = {}
    for rel in sorted(filtered_releases, key=lambda x: x["finish_date"]):
        finish_date = rel["finish_date"]
        start_date = shift_from_weekend(finish_date, -2)
        end_date = shift_from_weekend(finish_date, 2)

        fetched_releases[rel["version"]] = {
            "start_date": str(start_date),
            "end_date": str(end_date),
        }

    # Track updates and inserts
    updates = []  # List of [range, values]
    new_releases = []  # List of [version, start_date, end_date]
    rows_modified = 0

    # Update existing releases with new dates (preserve D-G)
    for version, dates in fetched_releases.items():
        if version in existing_releases:
            row_idx = existing_releases[version]
            row_num = row_idx + 1  # Convert to 1-based sheet row number

            # Update only columns B and C (start_date and end_date)
            updates.append(
                (f"B{row_num}:C{row_num}", [[dates["start_date"], dates["end_date"]]])
            )
            rows_modified += 1
        else:
            # New release - will be added later
            new_releases.append([version, dates["start_date"], dates["end_date"]])

    # Apply date updates for existing releases
    if updates:
        for range_name, values in updates:
            worksheet.update(values=values, range_name=range_name)

    # Add new releases to the end
    if new_releases:
        worksheet.append_rows(new_releases)
        rows_modified += len(new_releases)

    return rows_modified
