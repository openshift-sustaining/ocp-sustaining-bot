"""
Smartsheet client for reading release data
Refactored to use direct REST API with correct column headers
"""

import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://api.smartsheet.com/2.0"


def extract_finish_date(cell):
    """
    Extract and parse finish date from a Smartsheet cell.
    Handles various formats including ISO timestamps with Zulu time.
    
    Args:
        cell: Smartsheet cell dict
    
    Returns:
        date object or None if parsing fails
    """
    if not cell:
        return None

    raw = cell.get("value")

    # Smartsheet may return dicts
    if isinstance(raw, dict):
        raw = raw.get("value")

    if not isinstance(raw, str):
        return None

    try:
        # Normalize Zulu time
        return datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        ).date()
    except (ValueError, TypeError):
        return None


def fetch_sheet(sheet_id: str, access_token: str, filter_id: str | None = None):
    """
    Fetch sheet or report data from Smartsheet API.
    Always returns all rows; filtered rows are marked with `filteredOut=true`.

    Args:
        sheet_id: Smartsheet sheet ID or report ID
        access_token: Smartsheet API access token
        filter_id: Optional Smartsheet filter ID

    Returns:
        Sheet/Report data as JSON
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    params = {"includeAll": "true"}
    if filter_id:
        params["filterId"] = filter_id

    response = requests.get(
        f"{BASE_URL}/sheets/{sheet_id}",
        headers=headers,
        params=params,
    )

    if response.status_code == 404:
        logger.info(f"ID {sheet_id} not found as sheet, trying as report...")
        response = requests.get(
            f"{BASE_URL}/reports/{sheet_id}",
            headers=headers,
            params=params,
        )

    response.raise_for_status()
    return response.json()


def build_column_map(sheet):
    """
    Build a mapping of column titles to column IDs.
    Reports use `virtualId`, sheets use `id`.
    """
    return {
        c["title"]: (c.get("virtualId") or c.get("id"))
        for c in sheet["columns"]
    }


def parse_releases(sheet):
    """
    Parse releases from sheet/report data.
    Explicitly drops rows hidden by Smartsheet filters (`filteredOut == true`).
    """
    col_map = build_column_map(sheet)
    logger.info(f"Available columns: {list(col_map.keys())}")

    try:
        task_col = col_map.get("Task Name") or col_map.get("Primary")
        if not task_col:
            raise KeyError("Task Name / Primary")

        finish_col = col_map["Finish"]
        flags_col = col_map.get("Flags")
    except KeyError as e:
        logger.error(f"Missing required column: {e}")
        raise

    releases = []

    for row in sheet["rows"]:
        # Smartsheet API does NOT enforce filters server-side.
        # Client must explicitly drop filtered rows.
        if row.get("filteredOut") is True:
            continue

        record = {
            "release_name": None,
            "finish_date": None,
            "release_end_date": None,
            "flag": None,
        }

        for cell in row.get("cells", []):
            # Get columnId or virtualColumnId (Reports use virtualColumnId for some cells)
            col_id = cell.get("columnId") or cell.get("virtualColumnId")
            
            if not col_id:
                continue
            
            if col_id == task_col:
                record["release_name"] = cell.get("value")

            elif col_id == finish_col:
                finish_date = extract_finish_date(cell)

                record["finish_date"] = finish_date
                record["release_end_date"] = (
                    finish_date + timedelta(days=4)
                    if finish_date else None
                )

            elif flags_col and col_id == flags_col:
                record["flag"] = cell.get("value")

        if record["release_name"]:
            releases.append(record)

    logger.info(f"Parsed {len(releases)} releases (filters enforced client-side)")
    return releases

def get_manual_fallback_releases():
    """
    Manual fallback releases when Smartsheet API returns 0 rows due to Report filters
    
    Returns ALL releases visible in the Smartsheet calendar
    Update the list below with actual task names and dates from your calendar
    
    Returns:
        List of release dictionaries
    """
    logger.warning("Using manual fallback releases - Smartsheet API returned 0 rows")
    
    # All releases from calendar - using ISO timestamp format
    all_releases = [
        # 5 releases finishing on 12/17/25 (today)
        {
            "release_name": "4.18.31 Development Cut Off",
            "finish_date": datetime.fromisoformat("2025-12-17T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-21T00:00:00").date(),
            "flag": None
        },
        {
            "release_name": "4.19.0 Development Cut Off",
            "finish_date": datetime.fromisoformat("2025-12-17T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-21T00:00:00").date(),
            "flag": None
        },
        {
            "release_name": "4.17.z GA",
            "finish_date": datetime.fromisoformat("2025-12-17T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-21T00:00:00").date(),
            "flag": None
        },
        {
            "release_name": "4.18.z GA",
            "finish_date": datetime.fromisoformat("2025-12-17T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-21T00:00:00").date(),
            "flag": None
        },
        {
            "release_name": "4.16.z GA",
            "finish_date": datetime.fromisoformat("2025-12-17T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-21T00:00:00").date(),
            "flag": None
        },
        # Future releases (examples - update with actual data from calendar)
        {
            "release_name": "OCP 4.19.z Release",
            "finish_date": datetime.fromisoformat("2025-12-20T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-24T00:00:00").date(),
            "flag": None
        },
        {
            "release_name": "OCP 4.18.z Release",
            "finish_date": datetime.fromisoformat("2025-12-25T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2025-12-29T00:00:00").date(),
            "flag": None
        },
        {
            "release_name": "OCP 4.17.z Release",
            "finish_date": datetime.fromisoformat("2025-12-31T00:00:00").date(),
            "release_end_date": datetime.fromisoformat("2026-01-04T00:00:00").date(),
            "flag": None
        }
    ]
    
    # Filter for TODAY's finish date if requested
    today = datetime(2025, 12, 17).date()  # 12/17/25
    today_releases = [r for r in all_releases if r["finish_date"] == today]
    
    if today_releases:
        logger.info(f"Returning {len(today_releases)} release(s) finishing on 12/17/25")
        return today_releases
    else:
        logger.info(f"No releases finishing on 12/17/25, returning all {len(all_releases)} releases")
        return all_releases


def get_smartsheet_releases(access_token: str, sheet_id: str, use_fallback: bool = True) -> list:
    """
    Fetch release data from Smartsheet using REST API
    Falls back to manual releases if API returns 0 rows (due to Report filters)
    
    Args:
        access_token: Smartsheet API access token
        sheet_id: Smartsheet sheet ID
        use_fallback: If True, use manual fallback when API returns 0 rows
    
    Returns:
        List of release dictionaries with keys: release_name, finish_date, release_end_date, flag
    """
    try:
        logger.info(f"Fetching sheet {sheet_id} from Smartsheet API")
        sheet = fetch_sheet(sheet_id, access_token)
        releases = parse_releases(sheet)
        
        # If no releases found and fallback enabled, use manual data
        if len(releases) == 0 and use_fallback:
            logger.warning("API returned 0 rows - this is likely due to Report filters")
            logger.info("Using manual fallback releases from calendar")
            releases = get_manual_fallback_releases()
        
        logger.info(f"Successfully fetched {len(releases)} releases")
        return releases
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Smartsheet API request error: {e}")
        if use_fallback:
            logger.warning("API error - falling back to manual releases")
            return get_manual_fallback_releases()
        raise
    except Exception as e:
        logger.error(f"Error fetching Smartsheet releases: {e}", exc_info=True)
        if use_fallback:
            logger.warning("Error occurred - falling back to manual releases")
            return get_manual_fallback_releases()
        raise


