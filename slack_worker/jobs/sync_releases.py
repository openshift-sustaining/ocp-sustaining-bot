"""
Smartsheet sync job - fetches releases from Smartsheet and writes to Google Sheets
Runs daily at 8 AM
"""

import logging
import os
import re

from slack_worker.config import config
from sdk.smartsheet import (
    fetch_sheet_by_id,
    parse_sheet_releases,
    filter_releases,
    write_to_gsheet,
)

logger = logging.getLogger(__name__)


def _load_sheet_ids():
    """Dynamically load OCP version sheet IDs from environment variables.

    Scans all environment variables for SMARTSHEET_SHEET_*_ID pattern.
    Only includes versions that have actual IDs configured (ignores empty/commented vars).

    Pattern: SMARTSHEET_SHEET_<major>_<minor>_ID
    Examples:
        SMARTSHEET_SHEET_4_12_ID=7020066991564676  → "4.12": "7020066991564676"
        SMARTSHEET_SHEET_4_17_ID=...                → "4.17": "..."
        # SMARTSHEET_SHEET_4_21_ID=...              → (skipped - commented)

    To add a new OCP version:
        1. Uncomment SMARTSHEET_SHEET_4_XX_ID in .env
        2. Add the sheet ID
        3. Job automatically discovers and syncs it

    Returns:
        dict: Mapping of version strings to sheet IDs
              Example: {"4.12": "7020066991564676", "4.13": "3756051883052932"}
    """
    sheet_ids = {}
    # Pattern: SMARTSHEET_SHEET_4_XX_ID
    pattern = r"SMARTSHEET_SHEET_(\d+)_(\d+)_ID"

    for key, value in os.environ.items():
        match = re.match(pattern, key)
        if match and value:
            major = match.group(1)
            minor = match.group(2)
            version = f"{major}.{minor}"
            sheet_ids[version] = value

    return sheet_ids


# Load sheet IDs dynamically from .env - add/remove versions without code changes
SHEET_IDS = _load_sheet_ids()


def sync_releases_to_gsheet():
    """
    Main sync job - fetches from Smartsheet and writes to Google Sheets
    Runs daily at 8 AM UTC
    """
    logger.info("=" * 60)
    logger.info("STARTING RELEASES SYNC JOB")
    logger.info("=" * 60)

    try:
        from datetime import datetime

        logger.info(f"Job started at {datetime.now()}")

        smartsheet_token = config.SMARTSHEET_ACCESS_TOKEN
        gsheet_creds = config.ROTA_SERVICE_ACCOUNT
        logger.debug("Checking required environment variables")

        if not smartsheet_token:
            logger.error("  ✗ SMARTSHEET_ACCESS_TOKEN not found in environment")
            raise ValueError("SMARTSHEET_ACCESS_TOKEN not configured")
        logger.debug("  ✓ SMARTSHEET_ACCESS_TOKEN found")

        if not gsheet_creds:
            logger.error("  ✗ ROTA_SERVICE_ACCOUNT not found in environment")
            raise ValueError("ROTA_SERVICE_ACCOUNT not configured")
        logger.debug("  ✓ ROTA_SERVICE_ACCOUNT found")

        # Step 1: Fetch from Smartsheet
        logger.info("Step 1: Fetching data from OCP 4.12-4.16 Smartsheet sheets")
        all_releases = []
        fetch_count = 0

        for short_version, sheet_id in SHEET_IDS.items():
            if not sheet_id:
                logger.warning(
                    f"  ⊘ No Smartsheet ID configured for OCP {short_version}, skipping"
                )
                continue

            try:
                logger.debug(
                    f"  - Fetching OCP {short_version} (Sheet ID: {sheet_id[:8]}...)"
                )
                sheet_data = fetch_sheet_by_id(sheet_id, smartsheet_token)
                releases = parse_sheet_releases(sheet_data, short_version)
                all_releases.extend(releases)
                logger.info(
                    f"    ✓ OCP {short_version}: {len(releases)} releases fetched"
                )
                fetch_count += 1
            except Exception as e:
                logger.error(
                    f"    ✗ Error fetching OCP {short_version}: {e}", exc_info=True
                )

        logger.info(
            f"  ✓ Total releases fetched: {len(all_releases)} from {fetch_count} sheets"
        )

        # Step 2: Filter
        logger.info(
            "Step 2: Filtering releases by version, z-stream format, dev flag, and date range"
        )
        logger.debug(f"  - Input: {len(all_releases)} releases")
        filtered = filter_releases(all_releases)
        logger.info(
            f"  ✓ Filtered to {len(filtered)} releases (removed {len(all_releases) - len(filtered)})"
        )

        if filtered:
            logger.debug("  - Filtered releases:")
            for rel in filtered[:5]:  # Log first 5 for debugging
                logger.debug(f"    • {rel['version']} - {rel['finish_date']}")
            if len(filtered) > 5:
                logger.debug(f"    ... and {len(filtered) - 5} more")

        # Step 3: Write to Google Sheets
        logger.info(
            "Step 3: Writing releases to Google Sheets (ROTA -> Assignments worksheet)"
        )
        logger.debug(f"  - Preparing to write {len(filtered)} rows")
        rows_written = write_to_gsheet(filtered, gsheet_creds)
        logger.info(f"  ✓ Successfully wrote {rows_written} releases to Google Sheets")

        logger.info("=" * 60)
        logger.info("RELEASES SYNC JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error("RELEASES SYNC JOB FAILED")
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 60)
        raise
