#!/usr/bin/env python3
"""
Test script to send group reminder message (ignores day of week constraint)
Useful for manually testing the reminder outside of scheduled times
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
)
from slack_worker.slack_client import slack_client


def main():
    print("\n" + "=" * 80)
    print("📋 GROUP REMINDER TEST - Manual Send")
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

    # Build message
    print("\n🔨 Building message...")
    try:
        message_parts = [":robot_face: *ROTA Release Reminder*\n"]

        if current_releases:
            message_parts.append("*:calendar: This week release*\n")
            message_parts.append(format_release_message(current_releases, "This Week"))

        if next_releases:
            message_parts.append("\n*:calendar: Next release*\n")
            message_parts.append(format_release_message(next_releases, "Next Week"))

        if not current_releases and not next_releases:
            message_parts.append("No releases scheduled for this week or next week.")

        message = "\n".join(message_parts)
        print(f"✅ Message built ({len(message)} chars)")
    except Exception as e:
        print(f"❌ Error building message: {e}")
        import traceback

        traceback.print_exc()
        return

    # Preview
    print("\n" + "-" * 80)
    print("📌 MESSAGE PREVIEW:")
    print("-" * 80)
    print(message)
    print("-" * 80)

    # Confirm send
    print(f"\n🎯 Target Channel: {config.ROTA_GROUP_CHANNEL} (#rota-reminders)")
    response = input("\n🚀 Send this message? (yes/no): ").strip().lower()

    if response != "yes":
        print("❌ Cancelled - message not sent")
        return

    # Send
    print("\n📤 Sending message...")
    try:
        success = slack_client.send_message(
            channel=config.ROTA_GROUP_CHANNEL, text=message
        )

        if success:
            print("✅ Message sent successfully!")
        else:
            print("❌ Failed to send message")
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
