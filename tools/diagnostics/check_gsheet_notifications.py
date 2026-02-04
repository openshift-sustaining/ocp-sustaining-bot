#!/usr/bin/env python3
"""
Check notification data directly from Google Sheets
Displays what will be sent to Slack (channel and DMs)
"""

import os
import sys
from datetime import datetime

# Add project root to path (go up 3 levels: tools/diagnostics -> tools -> root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from config import config as parent_config
from sdk.gsheet.gsheet import GSheet
from slack_worker.config import config


def print_separator(title=""):
    """Print a visual separator"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def display_gsheet_data():
    """Fetch and display raw data from Google Sheets"""
    print_separator("STEP 1: Fetching Raw Data from Google Sheets")

    try:
        print(f"📋 Google Sheet ID: {parent_config.SPREADSHEET_ID}")
        print(
            f"🔐 Service Account: {parent_config.ROTA_SERVICE_ACCOUNT.get('client_email', 'N/A')}\n"
        )

        gsheet = GSheet(token=parent_config.ROTA_SERVICE_ACCOUNT)

        # Fetch this week
        print("📅 Fetching 'This Week' releases...\n")
        this_week_data = gsheet.fetch_data_by_time("This Week")

        if this_week_data:
            print("✅ THIS WEEK RELEASES:")
            print(
                f"{'Version':<15} {'Start':<15} {'End':<15} {'PM':<15} {'QE1':<15} {'QE2':<15}"
            )
            print("-" * 90)
            for row in this_week_data:
                version = row[0] if len(row) > 0 else "N/A"
                start = row[1] if len(row) > 1 else "N/A"
                end = row[2] if len(row) > 2 else "N/A"
                pm = row[3] if len(row) > 3 else "N/A"
                qe1 = row[4] if len(row) > 4 else "N/A"
                qe2 = row[5] if len(row) > 5 else "N/A"
                print(
                    f"{version:<15} {start:<15} {end:<15} {pm:<15} {qe1:<15} {qe2:<15}"
                )
        else:
            print("❌ No releases found for this week")

        # Fetch next week
        print("\n\n📅 Fetching 'Next Week' releases...\n")
        next_week_data = gsheet.fetch_data_by_time("Next Week")

        if next_week_data:
            print("✅ NEXT WEEK RELEASES:")
            print(
                f"{'Version':<15} {'Start':<15} {'End':<15} {'PM':<15} {'QE1':<15} {'QE2':<15}"
            )
            print("-" * 90)
            for row in next_week_data:
                version = row[0] if len(row) > 0 else "N/A"
                start = row[1] if len(row) > 1 else "N/A"
                end = row[2] if len(row) > 2 else "N/A"
                pm = row[3] if len(row) > 3 else "N/A"
                qe1 = row[4] if len(row) > 4 else "N/A"
                qe2 = row[5] if len(row) > 5 else "N/A"
                print(
                    f"{version:<15} {start:<15} {end:<15} {pm:<15} {qe1:<15} {qe2:<15}"
                )
        else:
            print("❌ No releases found for next week")

        return this_week_data, next_week_data

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return [], []


def display_user_mapping():
    """Show the user mapping that will be used for @mentions"""
    print_separator("STEP 2: User Mapping (Names → Slack IDs)")

    print("This mapping converts sheet names to Slack mentions:\n")
    print(f"{'Sheet Name':<20} {'Slack ID':<20} {'Slack Mention':<20}")
    print("-" * 60)

    for name, user_id in sorted(config.ROTA_USERS.items()):
        mention = f"<@{user_id}>"
        print(f"{name:<20} {user_id:<20} {mention:<20}")


def display_channel_notification(this_week_data, next_week_data):
    """Display what will be sent to the group channel"""
    print_separator("STEP 3: Channel Notification (GROUP REMINDER)")

    print(f"📢 Channel: {config.ROTA_GROUP_CHANNEL}")
    print(f"⏰ Sent: Monday & Thursday @ 9 AM\n")

    today = datetime.now().date()
    day_of_week = today.weekday()

    print(
        f"📅 Current day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week]}\n"
    )

    if day_of_week == 0:  # Monday
        print("🔔 On MONDAY, bot sends:\n")
    elif day_of_week == 3:  # Thursday
        print("🔔 On THURSDAY, bot sends:\n")
    else:
        print("ℹ️  (Not a Monday or Thursday, but here's what would be sent today)\n")

    # Simulate message
    message_parts = [":wave: *ROTA Release Reminder*\n"]

    if this_week_data:
        message_parts.append("*:calendar: Releases for This Week*\n")
        for row in this_week_data:
            version = row[0] if len(row) > 0 else "N/A"
            start = row[1] if len(row) > 1 else "N/A"
            end = row[2] if len(row) > 2 else "N/A"
            pm = row[3] if len(row) > 3 else "N/A"
            qe1 = row[4] if len(row) > 4 else "N/A"
            qe2 = row[5] if len(row) > 5 else "N/A"

            pm_mention = (
                f"<@{config.ROTA_USERS.get(pm)}>" if config.ROTA_USERS.get(pm) else pm
            )
            qe1_mention = (
                f"<@{config.ROTA_USERS.get(qe1)}>"
                if config.ROTA_USERS.get(qe1)
                else qe1
            )
            qe2_mention = (
                f"<@{config.ROTA_USERS.get(qe2)}>"
                if config.ROTA_USERS.get(qe2)
                else qe2
            )

            message_parts.append(
                f"\n*Release:* `{version}`\n"
                f"*Dates:* {start} to {end}\n"
                f"*Patch Manager:* {pm_mention}\n"
                f"*QE:* {qe1_mention}, {qe2_mention}\n"
            )
    else:
        message_parts.append("No releases this week.\n")

    if this_week_data and next_week_data:
        message_parts.append("\n" + "*:calendar: Releases for Next Week*\n")
        for row in next_week_data:
            version = row[0] if len(row) > 0 else "N/A"
            start = row[1] if len(row) > 1 else "N/A"
            end = row[2] if len(row) > 2 else "N/A"
            pm = row[3] if len(row) > 3 else "N/A"
            qe1 = row[4] if len(row) > 4 else "N/A"
            qe2 = row[5] if len(row) > 5 else "N/A"

            pm_mention = (
                f"<@{config.ROTA_USERS.get(pm)}>" if config.ROTA_USERS.get(pm) else pm
            )
            qe1_mention = (
                f"<@{config.ROTA_USERS.get(qe1)}>"
                if config.ROTA_USERS.get(qe1)
                else qe1
            )
            qe2_mention = (
                f"<@{config.ROTA_USERS.get(qe2)}>"
                if config.ROTA_USERS.get(qe2)
                else qe2
            )

            message_parts.append(
                f"\n*Release:* `{version}`\n"
                f"*Dates:* {start} to {end}\n"
                f"*Patch Manager:* {pm_mention}\n"
                f"*QE:* {qe1_mention}, {qe2_mention}\n"
            )

    message = "".join(message_parts)
    print("📬 MESSAGE THAT WILL BE POSTED:\n")
    print("┌" + "─" * 78 + "┐")
    for line in message.split("\n"):
        print(f"│ {line:<76} │")
    print("└" + "─" * 78 + "┘")


def display_dm_notifications(this_week_data):
    """Display what DMs will be sent to individuals"""
    print_separator("STEP 4: DM Notifications (INDIVIDUAL REMINDERS)")

    print(f"⏰ Sent: Friday @ 5 PM or Monday @ 9 AM\n")

    # Build people_to_notify dictionary
    people_to_notify = {}

    for row in this_week_data:
        pm = row[3] if len(row) > 3 else None
        qe1 = row[4] if len(row) > 4 else None
        qe2 = row[5] if len(row) > 5 else None

        # Add PM
        if pm and pm != "TBD":
            user_id = config.ROTA_USERS.get(pm)
            if user_id:
                if user_id not in people_to_notify:
                    people_to_notify[user_id] = {"name": pm, "assignments": []}
                people_to_notify[user_id]["assignments"].append(
                    {
                        "role": "Patch Manager",
                        "version": row[0],
                        "start": row[1],
                        "end": row[2],
                    }
                )

        # Add QE1
        if qe1 and qe1 != "TBD":
            user_id = config.ROTA_USERS.get(qe1)
            if user_id:
                if user_id not in people_to_notify:
                    people_to_notify[user_id] = {"name": qe1, "assignments": []}
                people_to_notify[user_id]["assignments"].append(
                    {"role": "QE", "version": row[0], "start": row[1], "end": row[2]}
                )

        # Add QE2
        if qe2 and qe2 != "TBD":
            user_id = config.ROTA_USERS.get(qe2)
            if user_id:
                if user_id not in people_to_notify:
                    people_to_notify[user_id] = {"name": qe2, "assignments": []}
                people_to_notify[user_id]["assignments"].append(
                    {"role": "QE", "version": row[0], "start": row[1], "end": row[2]}
                )

    if not people_to_notify:
        print("❌ No people to notify (no releases this week)\n")
        return

    print(f"✅ DMs will be sent to {len(people_to_notify)} people:\n")

    for user_id, user_info in sorted(
        people_to_notify.items(), key=lambda x: x[1]["name"]
    ):
        name = user_info["name"]
        assignments = user_info["assignments"]

        print(f"👤 {name.upper()} ({user_id})")
        print("   " + "─" * 75)

        message_parts = [
            ":wave: Just a reminder that you were on ROTA for this week:\n"
        ]

        for assignment in assignments:
            message_parts.append(
                f"\n*Release:* `{assignment['version']}`\n"
                f"*Your Role:* {assignment['role']}\n"
                f"*Dates:* {assignment['start']} to {assignment['end']}"
            )

        message_parts.append("\n\nThank you for your work! :rocket:")
        message = "".join(message_parts)

        print("\n   📬 DM MESSAGE:\n")
        for line in message.split("\n"):
            print(f"   │ {line}")

        print("\n")


def main():
    """Main function"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  📊 GOOGLE SHEETS NOTIFICATION DATA CHECK".center(78) + "║")
    print("║" + "  What will be sent to Slack (Channel & DMs)".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    # Step 1: Fetch raw data
    this_week_data, next_week_data = display_gsheet_data()

    # Step 2: Show user mapping
    display_user_mapping()

    # Step 3: Show channel notification
    display_channel_notification(this_week_data, next_week_data)

    # Step 4: Show DM notifications
    display_dm_notifications(this_week_data)

    print_separator("✅ CHECK COMPLETE!")
    print("Summary:")
    print(f"  • This Week Releases: {len(this_week_data)}")
    print(f"  • Next Week Releases: {len(next_week_data)}")
    print(f"  • Users in ROTA_USERS: {len(config.ROTA_USERS)}")
    print(f"  • Group Channel: {config.ROTA_GROUP_CHANNEL}")
    print(f"\n✨ All notifications are built from Google Sheets data!")
    print("\n")


if __name__ == "__main__":
    main()
