#!/usr/bin/env python3
"""
Preview and fire DM reminder notifications to individuals
Shows exactly who will get what message
"""

import logging
import os
import sys

# Add project root to path (go up 2 levels: scripts/notifications -> scripts -> root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from slack_worker.config import config
from slack_worker.jobs.rota_reminders import (
    get_current_week_releases,
    log_dm_notifications,
    send_dm_reminders,
)


def preview_and_send():
    """Preview DM reminders, then send them"""

    print("\n" + "=" * 100)
    print("DM REMINDER NOTIFICATIONS - PREVIEW & SEND")
    print("=" * 100 + "\n")

    # Step 1: Fetch data
    print("STEP 1: FETCHING DATA FROM GOOGLE SHEETS\n")
    print("-" * 100)

    releases = get_current_week_releases()

    if not releases:
        print("\n❌ No releases found for this week")
        print("No DMs will be sent.\n")
        return

    print(f"\n✅ Found {len(releases)} releases\n")

    # Step 2: Build notification list
    print("STEP 2: BUILDING DM RECIPIENTS\n")
    print("-" * 100)

    people_to_notify = {}

    for release in releases:
        pm = release.get("pm")
        qe1 = release.get("qe1")
        qe2 = release.get("qe2")

        # Add PM
        if pm and pm != "TBD":
            user_id = config.ROTA_USERS.get(pm)
            if user_id:
                if user_id not in people_to_notify:
                    people_to_notify[user_id] = {"name": pm, "assignments": []}
                people_to_notify[user_id]["assignments"].append(
                    {
                        "role": "Patch Manager",
                        "version": release.get("version"),
                    }
                )

        # Add QE1
        if qe1 and qe1 != "TBD":
            user_id = config.ROTA_USERS.get(qe1)
            if user_id:
                if user_id not in people_to_notify:
                    people_to_notify[user_id] = {"name": qe1, "assignments": []}
                people_to_notify[user_id]["assignments"].append(
                    {
                        "role": "QE",
                        "version": release.get("version"),
                    }
                )

        # Add QE2
        if qe2 and qe2 != "TBD":
            user_id = config.ROTA_USERS.get(qe2)
            if user_id:
                if user_id not in people_to_notify:
                    people_to_notify[user_id] = {"name": qe2, "assignments": []}
                people_to_notify[user_id]["assignments"].append(
                    {
                        "role": "QE",
                        "version": release.get("version"),
                    }
                )

    # Step 3: Log notifications
    print()
    log_dm_notifications(people_to_notify)

    # Step 4: Send
    print("=" * 100)
    print("STEP 3: SENDING DMs")
    print("=" * 100 + "\n")

    response = (
        input(
            f"🚀 Ready to send DMs to {len(people_to_notify)} people? Type 'yes' to confirm: "
        )
        .strip()
        .lower()
    )

    if response == "yes":
        print("\n📤 Sending DMs...\n")
        try:
            send_dm_reminders()
            print(f"\n✅ DMS SENT SUCCESSFULLY!")
            print(f"\n✨ Check your DMs - {len(people_to_notify)} people were notified!")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("\n⏸️  Cancelled. No DMs sent.")

    print("\n" + "=" * 100 + "\n")


if __name__ == "__main__":
    preview_and_send()
