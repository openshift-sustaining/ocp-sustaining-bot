"""
ROTA reminder jobs for Slack notifications
"""

import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sdk.gsheet.gsheet import GSheet
from slack_worker.config import worker_config
from slack_worker.slack_client import slack_client

logger = logging.getLogger(__name__)


def log_fetched_data(releases: List[Dict], week_label: str = "This Week"):
    """
    Log fetched release data in a formatted way

    Args:
        releases: List of release dictionaries
        week_label: Label for the week (e.g., "This Week", "Next Week")
    """
    if not releases:
        logger.info(f"📭 No releases found for {week_label.lower()}")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"📊 FETCHED DATA FROM GOOGLE SHEETS - {week_label.upper()}")
    logger.info(f"{'='*80}")
    logger.info(f"📋 Sheet: {worker_config.ROTA_SHEET}")
    logger.info(
        f"🔐 Service Account: {worker_config.ROTA_SERVICE_ACCOUNT.get('client_email', 'N/A') if isinstance(worker_config.ROTA_SERVICE_ACCOUNT, dict) else 'N/A'}"
    )
    logger.info(f"\n📋 RELEASES ({len(releases)} total):\n")

    for i, release in enumerate(releases, 1):
        logger.info(f"  Release #{i}:")
        logger.info(f"    Version:    {release.get('version', 'N/A')}")
        logger.info(f"    Start Date: {release.get('start_date', 'N/A')}")
        logger.info(f"    End Date:   {release.get('end_date', 'N/A')}")
        logger.info(
            f"    PM:         {release.get('pm', 'N/A')} → {worker_config.ROTA_USERS.get(release.get('pm', ''), 'Not mapped')}"
        )
        logger.info(
            f"    QE1:        {release.get('qe1', 'N/A')} → {worker_config.ROTA_USERS.get(release.get('qe1', ''), 'Not mapped')}"
        )
        logger.info(
            f"    QE2:        {release.get('qe2', 'N/A')} → {worker_config.ROTA_USERS.get(release.get('qe2', ''), 'Not mapped')}"
        )
        logger.info(f"")

    logger.info(f"{'='*80}\n")


def log_dm_notifications(people_to_notify: Dict):
    """
    Log DM notifications that will be sent

    Args:
        people_to_notify: Dictionary mapping user_id to their assignments
    """
    if not people_to_notify:
        logger.info("📭 No DMs to send")
        return

    logger.info(f"\n{'='*80}")
    logger.info(f"💬 DM NOTIFICATIONS - {len(people_to_notify)} people")
    logger.info(f"{'='*80}\n")

    for user_id, user_info in sorted(
        people_to_notify.items(), key=lambda x: x[1].get("name", "Unknown")
    ):
        name = user_info.get("name", "Unknown")
        assignments = user_info.get("assignments", [])

        logger.info(f"👤 {name.upper()} ({user_id})")
        logger.info(f"   Assignments: {len(assignments)}")

        for assignment in assignments:
            logger.info(f"     • {assignment['version']} - {assignment['role']}")

        logger.info(f"")

    logger.info(f"{'='*80}\n")


def get_current_week_releases() -> List[Dict]:
    """
    Get releases for the current week from Google Sheets

    Returns:
        List of release data dictionaries
    """
    try:
        gsheet = GSheet(token=worker_config.ROTA_SERVICE_ACCOUNT)
        data = gsheet.fetch_data_by_time("This Week")

        if not data:
            logger.info("No releases found for current week")
            return []

        # Convert to list of dicts for easier processing
        releases = []
        for row in data:
            if len(row) >= 7:
                release = {
                    "version": row[0],
                    "start_date": row[1],
                    "end_date": row[2],
                    "pm": row[3],
                    "qe1": row[4],
                    "qe2": row[5],
                    "activity": row[6] if len(row) > 6 else "",
                }
                releases.append(release)

        logger.info(f"Found {len(releases)} release(s) for current week")
        # Log the fetched data
        log_fetched_data(releases, "This Week")
        return releases

    except Exception as e:
        logger.error(f"Error fetching current week releases: {e}", exc_info=True)
        return []


def get_next_week_releases() -> List[Dict]:
    """
    Get releases for the next week from Google Sheets

    Returns:
        List of release data dictionaries
    """
    try:
        gsheet = GSheet(token=worker_config.ROTA_SERVICE_ACCOUNT)
        data = gsheet.fetch_data_by_time("Next Week")

        if not data:
            logger.info("No releases found for next week")
            return []

        # Convert to list of dicts
        releases = []
        for row in data:
            if len(row) >= 7:
                release = {
                    "version": row[0],
                    "start_date": row[1],
                    "end_date": row[2],
                    "pm": row[3],
                    "qe1": row[4],
                    "qe2": row[5],
                    "activity": row[6] if len(row) > 6 else "",
                }
                releases.append(release)

        logger.info(f"Found {len(releases)} release(s) for next week")
        # Log the fetched data
        log_fetched_data(releases, "Next Week")
        return releases

    except Exception as e:
        logger.error(f"Error fetching next week releases: {e}", exc_info=True)
        return []


def format_release_message(releases: List[Dict], week_label: str = "This Week") -> str:
    """
    Format release information into a readable message

    Args:
        releases: List of release dictionaries
        week_label: Label for the week (e.g., "This Week", "Next Week")

    Returns:
        Formatted message string
    """
    if not releases:
        return f"No releases scheduled for {week_label.lower()}."

    message_parts = []

    for release in releases:
        pm = release.get("pm", "TBD")
        qe1 = release.get("qe1", "TBD")
        qe2 = release.get("qe2", "TBD")

        # Try to convert user names to Slack mentions with visible names
        pm_mention = get_user_mention(pm)
        qe1_mention = get_user_mention(qe1)
        qe2_mention = get_user_mention(qe2)

        # Build message parts
        message_text = (
            f"\n*Release:* `{release['version']}`\n"
            f"*Development Cut-off:* {release['start_date']}\n"
            f"*Fast-Channel:* {release['end_date']}\n"
            f"*Patch Manager:* {pm_mention}\n"
            f"*QE:* {qe1_mention}, {qe2_mention}\n"
        )

        # Add status only for "This Week"
        if "This Week" in week_label:
            message_text += "*✅ Status: Active*\n"

        message_parts.append(message_text)

    return "\n".join(message_parts)


def get_user_mention(username: str) -> str:
    """
    Convert username to Slack mention format

    Args:
        username: Username or display name

    Returns:
        Slack mention string
    """
    if not username or username == "TBD":
        return username

    # Check if username is in ROTA_USERS mapping
    user_id = worker_config.ROTA_USERS.get(username)
    if user_id:
        return f"<@{user_id}>"

    return username


def send_group_reminder():
    """
    Send group reminder about the week's releases
    Posted every Monday and Thursday
    """
    logger.info("Starting group reminder job")

    try:
        # Determine which week(s) to include based on day of week
        today = datetime.now().date()
        day_of_week = today.weekday()  # 0 = Monday, 3 = Thursday

        if day_of_week == 0:  # Monday
            # Show current week and next week
            current_releases = get_current_week_releases()
            next_releases = get_next_week_releases()

            message_parts = [":robot_face: *ROTA Release Reminder*\n"]

            if current_releases:
                message_parts.append("*:calendar: This week release*\n")
                message_parts.append(
                    format_release_message(current_releases, "This Week")
                )

            if next_releases:
                message_parts.append("\n*:calendar: Next release*\n")
                message_parts.append(format_release_message(next_releases, "Next Week"))

            if not current_releases and not next_releases:
                message_parts.append(
                    "No releases scheduled for this week or next week."
                )

            message = "\n".join(message_parts)

        elif day_of_week == 3:  # Thursday
            # Show current week only (mid-week update)
            current_releases = get_current_week_releases()

            message_parts = [":robot_face: *Mid-Week ROTA Reminder*\n"]

            if current_releases:
                message_parts.append(
                    format_release_message(current_releases, "This Week")
                )
            else:
                message_parts.append("No releases scheduled for this week.")

            message = "\n".join(message_parts)
        else:
            logger.warning(f"Group reminder triggered on unexpected day: {day_of_week}")
            return

        # Send to group channel
        if worker_config.ROTA_GROUP_CHANNEL:
            success = slack_client.send_message(
                channel=worker_config.ROTA_GROUP_CHANNEL, text=message
            )

            if success:
                logger.info("Group reminder sent successfully")
            else:
                logger.error("Failed to send group reminder")
        else:
            logger.warning("ROTA_GROUP_CHANNEL not configured, skipping group reminder")

    except Exception as e:
        logger.error(f"Error in group reminder job: {e}", exc_info=True)
        raise


def send_dm_reminders():
    """
    Send DM reminders to individuals about their releases
    - Friday: Reminder about previous week
    - Monday: Reminder about current week
    """
    logger.info("Starting DM reminder job")

    try:
        today = datetime.now().date()
        day_of_week = today.weekday()  # 0 = Monday, 4 = Friday

        if day_of_week == 4:  # Friday
            # Send reminders about current week (which is ending)
            releases = get_current_week_releases()
            week_label = "this week"
            message_prefix = ":robot_face: Just a reminder that you were on ROTA for"

        elif day_of_week == 0:  # Monday
            # Send reminders about current week (which is starting)
            releases = get_current_week_releases()
            week_label = "this week"
            message_prefix = ":bell: Reminder: You are on ROTA for"

        else:
            logger.warning(f"DM reminder triggered on unexpected day: {day_of_week}")
            return

        if not releases:
            logger.info(f"No releases for {week_label}, no DMs to send")
            return

        # Send DMs to each person involved in releases
        people_to_notify = {}  # user_id -> list of releases

        for release in releases:
            # Add PM
            pm = release.get("pm")
            if pm and pm != "TBD":
                user_id = worker_config.ROTA_USERS.get(pm)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": pm, "assignments": []}
                    people_to_notify[user_id]["assignments"].append(
                        {
                            "role": "Patch Manager",
                            "version": release.get("version"),
                            "release": release,
                        }
                    )

            # Add QE1
            qe1 = release.get("qe1")
            if qe1 and qe1 != "TBD":
                user_id = worker_config.ROTA_USERS.get(qe1)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": qe1, "assignments": []}
                    people_to_notify[user_id]["assignments"].append(
                        {
                            "role": "QE",
                            "version": release.get("version"),
                            "release": release,
                        }
                    )

            # Add QE2
            qe2 = release.get("qe2")
            if qe2 and qe2 != "TBD":
                user_id = worker_config.ROTA_USERS.get(qe2)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": qe2, "assignments": []}
                    people_to_notify[user_id]["assignments"].append(
                        {
                            "role": "QE",
                            "version": release.get("version"),
                            "release": release,
                        }
                    )

        # Log the DM notifications
        log_dm_notifications(people_to_notify)

        # Send DM to each person
        for user_id, user_info in people_to_notify.items():
            assignments = user_info.get("assignments", [])
            name = user_info.get("name", "Sustain-er")

            # Build friendly message
            message_parts = [f":robot_face: Hey {name}!\n"]
            message_parts.append(
                "You're on :threadparrot: ROTA this week! Here's what you're sustaining:\n"
            )

            for assignment in assignments:
                release = assignment["release"]
                role = assignment["role"]
                message_parts.append(
                    f"\n :calendar: Release *{release['version']}* - {role}"
                )

            message_parts.append(
                "\n\nKeep the builds running smoothly! :rocket:\nYou've got this! :mechanical_arm:"
            )
            message = "\n".join(message_parts)

            success = slack_client.send_dm(user_id=user_id, text=message)

            if success:
                logger.info(f"Sent DM reminder to user {user_id}")
            else:
                logger.error(f"Failed to send DM reminder to user {user_id}")

        logger.info(f"Completed DM reminders for {len(people_to_notify)} people")
    except Exception as e:
        logger.error(f"Error in DM reminder job: {e}", exc_info=True)
        raise


def send_dm_reminders_force():
    """
    Force send DM reminders regardless of day of week (for testing)
    Same as send_dm_reminders() but bypasses day-of-week check
    """
    logger.info("Starting DM reminder job (FORCED - testing mode)")

    try:
        # Always use Monday message for testing
        releases = get_current_week_releases()
        week_label = "this week"
        message_prefix = ":bell: Reminder: You are on ROTA for"

        if not releases:
            logger.info(f"No releases for {week_label}, no DMs to send")
            return

        # Send DMs to each person involved in releases
        people_to_notify = {}  # user_id -> list of releases

        for release in releases:
            # Add PM
            pm = release.get("pm")
            if pm and pm != "TBD":
                user_id = worker_config.ROTA_USERS.get(pm)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": pm, "assignments": []}
                    people_to_notify[user_id]["assignments"].append(
                        {
                            "role": "Patch Manager",
                            "version": release.get("version"),
                            "release": release,
                        }
                    )

            # Add QE1
            qe1 = release.get("qe1")
            if qe1 and qe1 != "TBD":
                user_id = worker_config.ROTA_USERS.get(qe1)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": qe1, "assignments": []}
                    people_to_notify[user_id]["assignments"].append(
                        {
                            "role": "QE",
                            "version": release.get("version"),
                            "release": release,
                        }
                    )

            # Add QE2
            qe2 = release.get("qe2")
            if qe2 and qe2 != "TBD":
                user_id = worker_config.ROTA_USERS.get(qe2)
                if user_id:
                    if user_id not in people_to_notify:
                        people_to_notify[user_id] = {"name": qe2, "assignments": []}
                    people_to_notify[user_id]["assignments"].append(
                        {
                            "role": "QE",
                            "version": release.get("version"),
                            "release": release,
                        }
                    )

        # Log the DM notifications
        log_dm_notifications(people_to_notify)

        # Send DM to each person
        for user_id, user_info in people_to_notify.items():
            assignments = user_info.get("assignments", [])
            name = user_info.get("name", "Sustain-er")

            # Build friendly message
            message_parts = [f":robot_face: Hey {name}!\n"]
            message_parts.append(
                "You're on :threadparrot: ROTA this week! Here's what you're sustaining:\n"
            )

            for assignment in assignments:
                release = assignment["release"]
                role = assignment["role"]
                message_parts.append(
                    f"\n :calendar: Release *{release['version']}* - {role}"
                )

            message_parts.append(
                "\n\nKeep the builds running smoothly! :rocket:\nYou've got this! :mechanical_arm:"
            )
            message = "\n".join(message_parts)

            success = slack_client.send_dm(user_id=user_id, text=message)

            if success:
                logger.info(f"Sent DM reminder to user {user_id}")
            else:
                logger.error(f"Failed to send DM reminder to user {user_id}")

        logger.info(f"Completed DM reminders for {len(people_to_notify)} people")
    except Exception as e:
        logger.error(f"Error in DM reminder job (forced): {e}", exc_info=True)
        raise
