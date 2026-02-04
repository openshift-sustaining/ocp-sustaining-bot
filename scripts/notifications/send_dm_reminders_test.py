#!/usr/bin/env python3
"""
Test script to send DM reminders (ignores day of week constraint)
Useful for manually testing DM notifications outside of scheduled times
"""

import os
import sys
from datetime import datetime

# Add project root to path (go up 2 levels: scripts/notifications -> scripts -> root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from slack_worker.config import config
from slack_worker.jobs.rota_reminders import (
    format_release_message,
    get_current_week_releases,
    get_next_week_releases,
    send_dm_reminders,
)


def main():
    print("\n" + "=" * 80)
    print("💬 DM REMINDER TEST - Manual Send")
    print("=" * 80)

    # Get today's info
    today = datetime.now().date()
    day_of_week = today.weekday()  # 0 = Monday, 6 = Sunday
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    print(f"\n📅 Current Date: {today} ({days[day_of_week]})")
    print(f"⏰ Time: {datetime.now().time()}")

    # Fetch data
    print("\n📡 Fetching release data from Google Sheets...")
    try:
        current_releases = get_current_week_releases()
        next_releases = get_next_week_releases()
        print(f"✅ This week:  {len(current_releases)} release(s)")
        print(f"✅ Next week:  {len(next_releases)} release(s)")
    except Exception as e:
        print(f"❌ Error fetching releases: {e}")
        return

    # Show who will get DMs
    print("\n📋 DMs will be sent to:")
    print(f"   PMs and QEs involved in current/next week releases")

    print(f"\n🎯 DM Scope Status:")
    print(f"   Required: im:write scope ⚠️ (may not be installed)")

    # Confirm send
    response = input("\n🚀 Send DM reminders? (yes/no): ").strip().lower()

    if response != "yes":
        print("❌ Cancelled - DMs not sent")
        return

    # Send
    print("\n📤 Sending DMs...")
    try:
        result = send_dm_reminders()
        print(f"\n✅ DM job completed!")
    except Exception as e:
        print(f"❌ Error sending DMs: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
