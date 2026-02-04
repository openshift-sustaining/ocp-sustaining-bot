#!/usr/bin/env python3
"""
Preview and fire group reminder notification to Slack
Shows exactly what will be sent before posting

NOTE: The scheduled send_group_reminder() only works on Monday & Thursday
If you run this on other days, it will check the day and may not send
Use send_group_reminder_test.py to force-send on any day
"""

import logging
import os
import sys
from datetime import datetime

# Add project root to path (go up 2 levels: scripts/notifications -> scripts -> root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Configure logging to see all output
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from slack_worker.config import config
from slack_worker.jobs.rota_reminders import (
    format_release_message,
    get_current_week_releases,
    get_next_week_releases,
    send_group_reminder,
)


def preview_and_send():
    """Preview what will be sent, then send it"""

    print("\n" + "=" * 100)
    print("GROUP REMINDER NOTIFICATION - PREVIEW & SEND")
    print("=" * 100 + "\n")

    # Check day of week
    today = datetime.now().date()
    day_of_week = today.weekday()  # 0 = Monday, 3 = Thursday
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    print(f"⚠️  Today is {days[day_of_week]} (Jan 27)")
    print(f"📋 Scheduled reminders only run on:")
    print(f"   • Monday: Send current week + next week")
    print(f"   • Thursday: Send current week only")
    print(f"   • Other days: Will be skipped by send_group_reminder()\n")

    if day_of_week not in [0, 3]:
        print(f"⚠️  Since today is NOT Monday or Thursday:")
        print(f"   send_group_reminder() will check the day and NOT send")
        print(f"   ➡️  Use send_group_reminder_test.py to force-send on any day\n")

    # Step 1: Preview
    print("STEP 1: FETCHING DATA FROM GOOGLE SHEETS\n")
    print("-" * 100)

    current_releases = get_current_week_releases()
    next_releases = get_next_week_releases()

    print(f"\n✅ Current week releases: {len(current_releases)}")
    print(f"✅ Next week releases: {len(next_releases)}\n")

    # Step 2: Format message
    print("STEP 2: FORMATTING MESSAGE FOR SLACK\n")
    print("-" * 100)

    if current_releases:
        current_msg = format_release_message(current_releases, "This Week")
        print("\n📢 THIS WEEK MESSAGE:\n")
        print(current_msg)

    if next_releases:
        next_msg = format_release_message(next_releases, "Next Week")
        print("\n📢 NEXT WEEK MESSAGE:\n")
        print(next_msg)

    # Step 3: Show target
    print("\n" + "=" * 100)
    print("STEP 3: TARGET CHANNEL")
    print("=" * 100 + "\n")

    print(f"📍 Channel: {config.ROTA_GROUP_CHANNEL}")
    print(f"🤖 Bot: ROTA Bot")
    print(f"⏰ Scheduled: Monday & Thursday @ 9 AM\n")

    # Step 4: Send
    print("=" * 100)
    print("STEP 4: SENDING TO SLACK")
    print("=" * 100 + "\n")

    response = input("🚀 Ready to send? Type 'yes' to confirm: ").strip().lower()

    if response == "yes":
        print("\n📤 Sending notification...\n")
        try:
            send_group_reminder()
            print("\n✅ NOTIFICATION SENT SUCCESSFULLY!")
            print("\n✨ Check #rota-reminders channel to see the message!")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("\n⏸️  Cancelled. No notification sent.")

    print("\n" + "=" * 100 + "\n")


if __name__ == "__main__":
    preview_and_send()
