#!/usr/bin/env python3
"""
Check Smartsheet connectivity and list report with all sheets
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path (go up 3 levels: tools/diagnostics -> tools -> root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

load_dotenv()


def check_connectivity():
    """Check Smartsheet connectivity and list report + sheets"""
    print("=" * 100)
    print("SMARTSHEET CONNECTIVITY CHECK")
    print("=" * 100)

    token = os.getenv("SMARTSHEET_ACCESS_TOKEN")
    report_id = os.getenv("SMARTSHEET_REPORT_ID")

    if not token:
        print("ERROR: SMARTSHEET_ACCESS_TOKEN not found in environment")
        return False

    print(f"✓ Token found (length: {len(token)} chars)")
    print(f"✓ Report ID: {report_id}")

    try:
        import smartsheet

        client = smartsheet.Smartsheet(token)
        client.errors_as_exceptions(True)

        # Step 1: Test authentication
        print("\n" + "=" * 100)
        print("STEP 1: AUTHENTICATION TEST")
        print("=" * 100)

        user = client.Users.get_current_user()
        user_dict = user.to_dict() if hasattr(user, "to_dict") else user

        user_name = user_dict.get("name", "Unknown")
        user_email = user_dict.get("email", "Unknown")

        print(f"✓ Authentication successful!")
        print(f"  User: {user_name}")
        print(f"  Email: {user_email}")

        # Step 2: List all sheets
        print("\n" + "=" * 100)
        print("STEP 2: LIST ALL SHEETS")
        print("=" * 100)

        sheets_list = client.Sheets.list_sheets()
        sheets_data = getattr(sheets_list, "data", [])

        print(f"✓ Found {len(sheets_data)} accessible sheets:\n")

        sheet_mapping = {}
        for i, sheet in enumerate(sheets_data, 1):
            sheet_id = getattr(sheet, "id", None)
            sheet_name = getattr(sheet, "name", None)
            row_count = getattr(sheet, "totalRowCount", "N/A")
            col_count = getattr(sheet, "columnCount", "N/A")

            sheet_mapping[sheet_id] = sheet_name

            print(f"  {i}. {sheet_name}")
            print(f"     ID: {sheet_id}")
            print(f"     Rows: {row_count}, Columns: {col_count}")

        # Step 3: Fetch and analyze report
        print("\n" + "=" * 100)
        print("STEP 3: FETCH REPORT")
        print("=" * 100)

        print(f"\nFetching report {report_id}...")
        report = client.Reports.get_report(int(report_id))
        report_dict = report.to_dict() if hasattr(report, "to_dict") else report

        report_name = report_dict.get("name", "Unknown")
        report_rows = report_dict.get("rows", [])
        report_columns = report_dict.get("columns", [])

        print(f"✓ Report fetched successfully!")
        print(f"  Name: {report_name}")
        print(f"  Total rows: {len(report_rows)}")
        print(f"  Total columns: {len(report_columns)}")

        # Step 4: Analyze report columns
        print("\n" + "=" * 100)
        print("STEP 4: REPORT COLUMNS")
        print("=" * 100)

        print(f"\nReport has {len(report_columns)} columns:\n")
        for i, col in enumerate(report_columns, 1):
            col_id = col.get("id")
            col_title = col.get("title")
            col_type = col.get("type")

            print(f"  {i}. {col_title}")
            print(f"     ID: {col_id}")
            print(f"     Type: {col_type}")

        # Step 5: Extract unique source sheets from report
        print("\n" + "=" * 100)
        print("STEP 5: REPORT SOURCE SHEETS")
        print("=" * 100)

        unique_sheet_ids = set()
        sheet_row_count = {}

        for row in report_rows:
            sheet_id = row.get("sheetId")
            if sheet_id:
                unique_sheet_ids.add(sheet_id)
                sheet_row_count[sheet_id] = sheet_row_count.get(sheet_id, 0) + 1

        print(f"\nReport references {len(unique_sheet_ids)} unique source sheets:\n")

        for sheet_id in sorted(unique_sheet_ids):
            sheet_name = sheet_mapping.get(sheet_id, f"Sheet_{sheet_id}")
            row_count = sheet_row_count[sheet_id]

            print(f"  • {sheet_name}")
            print(f"    ID: {sheet_id}")
            print(f"    Rows in report: {row_count}")

        # Step 6: Summary
        print("\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)

        print(
            f"""
✓ Connectivity: SUCCESSFUL
✓ Authentication: {user_name} <{user_email}>
✓ Total sheets accessible: {len(sheets_data)}
✓ Report name: {report_name}
✓ Report rows: {len(report_rows)}
✓ Report columns: {len(report_columns)}
✓ Sheets referenced in report: {len(unique_sheet_ids)}

All systems operational!
"""
        )

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_connectivity()
    sys.exit(0 if success else 1)
