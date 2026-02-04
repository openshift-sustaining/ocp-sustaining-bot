#!/usr/bin/env python3
"""
Test script to send DM reminders (ignores day of week constraint - for testing)
Useful for manually testing DM notifications outside of Monday/Friday
Shows detailed diagnostic info about who will receive DMs
"""

import os
import sys
from datetime import datetime

# Add project root to path (go up 2 levels: scripts/notifications -> scripts -> root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from slack_worker.config import config
from slack_worker.jobs.rota_reminders import (
    get_current_week_releases,
    send_dm_reminders_force,
)


def main():
    print("\n" + "=" * 80)
    print("💬 DM REMINDER TEST - Forced Send (Ignores Day of Week)")
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
    print("⚠️  Note: This is FORCED SEND mode - bypasses the Monday/Friday check")

    # Fetch data
    print("\n" + "-" * 80)
    print("📡 FETCHING RELEASE DATA")
    print("-" * 80)
    try:
        current_releases = get_current_week_releases()
        print(f"✅ This week:  {len(current_releases)} release(s)")

        if current_releases:
            for i, release in enumerate(current_releases, 1):
                print(f"\n   Release #{i}: {release.get('version')}")
                print(f"     PM:  {release.get('pm')}")
                print(f"     QE1: {release.get('qe1')}")
                print(f"     QE2: {release.get('qe2')}")
    except Exception as e:
        print(f"❌ Error fetching releases: {e}")
        return

    # Show who will get DMs
    print("\n" + "-" * 80)
    print("� WHO WILL GET DMs")
    print("-" * 80)
    people_to_notify = {}

    for release in current_releases:
        for role_key, role_name in [
            ("pm", "Patch Manager"),
            ("qe1", "QE"),
            ("qe2", "QE"),
        ]:
            person = release.get(role_key)
            if person and person != "TBD":
                user_id = config.ROTA_USERS.get(person)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": person, "roles": []}
                    people_to_notify[user_id]["roles"].append(
                        f"{role_name} for {release.get('version')}"
                    )
                else:
                    print(f"   ⚠️  {person} is NOT in ROTA_USERS mapping!")

    if people_to_notify:
        for user_id, info in people_to_notify.items():
            print(f"\n   ✅ {info['name']} ({user_id})")
            for role in info["roles"]:
                print(f"      • {role}")
    else:
        print("   ⚠️  No one will get DMs!")

    # Confirm send
    print("\n" + "-" * 80)
    response = input("🚀 Send DM reminders? (yes/no): ").strip().lower()

    if response != "yes":
        print("❌ Cancelled - DMs not sent")
        return

    # Send
    print("\n📤 SENDING DMs...")
    print("-" * 80)
    try:
        send_dm_reminders_force()
        print("\n✅ DM reminders sent!")
    except Exception as e:
        print(f"❌ Error sending DMs: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
