"""
ROTA notification job - sends both group reminders and DM reminders
Runs: Monday 9 AM (group + DM), Thursday 9 AM (group), Friday 5 PM (DM)
Writes notifications to Slack channel and DMs
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List

from slack_worker.config import config
from slack_worker.slack_client import slack_client
from sdk.gsheet.gsheet import GSheet

logger = logging.getLogger(__name__)


def get_this_week_monday() -> date:
    """Get this week's Monday date"""
    today = datetime.now().date()
    weekday = today.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday

    if weekday == 0:  # Already Monday
        return today
    else:
        # Go back to this week's Monday
        return today - timedelta(days=weekday)


def get_next_available_monday(assignment_wsheet) -> date:
    """Get the next Monday that has releases in the sheet (could be 1+ weeks away)

    Args:
        assignment_wsheet: The worksheet to search for available Mondays

    Returns:
        The earliest Monday date after this week that has at least one release,
        or next week's Monday if no releases are found
    """
    this_week_monday = get_this_week_monday()
    values = assignment_wsheet.get_values("G:G")  # Get all column G values (ERR dates)

    if not values:
        return this_week_monday + timedelta(days=7)

    # Collect all Monday dates in column G, filter for dates after this week
    future_mondays = set()
    for row in values[1:]:  # Skip header
        if row and len(row) > 0 and row[0]:
            try:
                monday_date = datetime.strptime(row[0], "%Y-%m-%d").date()
                if monday_date > this_week_monday:
                    future_mondays.add(monday_date)
            except (ValueError, IndexError):
                continue

    # Return the earliest future Monday, or default to next week
    return (
        min(future_mondays)
        if future_mondays
        else (this_week_monday + timedelta(days=7))
    )


def _parse_releases_from_rows(data: List[List]) -> List[Dict]:
    """
    Parse raw Google Sheets rows into release dictionaries

    Args:
        data: List of rows from Google Sheets (each row is a list)

    Returns:
        List of release dictionaries with version, dates, and team info
    """
    releases = []
    for row in data:
        if len(row) >= 6:
            release = {
                "version": row[0],
                "start_date": row[1],
                "end_date": row[2],
                "pm": row[3],
                "qe1": row[4],
                "qe2": row[5],
            }
            releases.append(release)
            logger.debug(f"    • Parsed release: {row[0]}")

    return releases


def get_current_week_releases() -> List[Dict]:
    """
    Get releases for the current week from Google Sheets
    (Releases with ERR date = this week's Monday)

    Returns:
        List of release data dictionaries
    """
    logger.debug("Step 1: Fetching current week releases from Google Sheets")
    try:
        gsheet = GSheet(token=config.ROTA_SERVICE_ACCOUNT)
        logger.debug("  - Google Sheets client initialized")

        this_week_monday = get_this_week_monday()
        logger.debug(f"  - This week's Monday: {this_week_monday}")

        data = gsheet.fetch_data_by_weekId(this_week_monday)
        logger.debug(f"  - Fetched raw data, rows count: {len(data) if data else 0}")

        if not data:
            logger.info("  ✗ No releases found for current week")
            return []

        releases = _parse_releases_from_rows(data)
        logger.info(f"  ✓ Found {len(releases)} release(s) for current week")
        return releases

    except Exception as e:
        logger.error(f"  ✗ Error fetching current week releases: {e}", exc_info=True)
        return []


def get_next_releases() -> List[Dict]:
    """
    Get releases for the next week from Google Sheets
    (Releases with ERR date = next available Monday with releases)

    Returns:
        List of release data dictionaries
    """
    logger.debug("Step 2: Fetching next week releases from Google Sheets")
    try:
        gsheet = GSheet(token=config.ROTA_SERVICE_ACCOUNT)
        logger.debug("  - Google Sheets client initialized")

        next_monday = get_next_available_monday(gsheet._assignment_wsheet)
        logger.debug(f"  - Next available Monday: {next_monday}")

        data = gsheet.fetch_data_by_weekId(next_monday)
        logger.debug(f"  - Fetched raw data, rows count: {len(data) if data else 0}")

        if not data:
            logger.info("  ✗ No releases found for next week")
            return []

        releases = _parse_releases_from_rows(data)
        logger.info(f"  ✓ Found {len(releases)} release(s) for next week")
        return releases

    except Exception as e:
        logger.error(f"  ✗ Error fetching next week releases: {e}", exc_info=True)
        return []


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

    user_id = config.ROTA_USERS.get(username)
    if user_id:
        return f"<@{user_id}>"

    return username


def format_release_message(releases: List[Dict], week_label: str = "This Week") -> str:
    """
    Format release information into a readable message

    Args:
        releases: List of release dictionaries
        week_label: Label for the week (e.g., "This Week", "Next Week")

    Returns:
        Formatted message string
    """
    logger.debug(f"Step 3: Formatting {len(releases)} releases for '{week_label}'")
    if not releases:
        logger.debug("  - No releases to format")
        return f"No releases scheduled for {week_label.lower()}."

    message_parts = []

    for release in releases:
        pm = release.get("pm", "TBD")
        qe1 = release.get("qe1", "TBD")
        qe2 = release.get("qe2", "TBD")
        logger.debug(
            f"  • Formatting {release['version']}: PM={pm}, QE1={qe1}, QE2={qe2}"
        )

        pm_mention = get_user_mention(pm)
        qe1_mention = get_user_mention(qe1)
        qe2_mention = get_user_mention(qe2)

        message_text = (
            f"*Release:* `{release['version']}`\n"
            f":calendar: *Development Cut-off:* {release['start_date']}\n"
            f":calendar: *Fast-Channel:* {release['end_date']}\n"
            f"*Patch Manager:* {pm_mention}\n"
            f"*QE:* {qe1_mention}, {qe2_mention}\n"
        )

        if "This Week" in week_label:
            message_text += "*Status: :green-circle-small: Active*\n"

        message_parts.append(message_text)

    logger.debug(f"  ✓ Formatted message with {len(message_parts)} release(s)")
    return "\n".join(message_parts)


def send_group_reminder():
    """
    Send group reminder about the week's releases
    Posted every Monday and Thursday at 9 AM

    Monday 9 AM: Current week + Next week (if found)
    Thursday 9 AM: Same current week releases (reminder)
    """
    logger.info("Step 4a: Sending group reminder to Slack channel")

    try:
        today = datetime.now().date()
        day_of_week = today.weekday()  # 0 = Monday, 3 = Thursday
        logger.debug(f"  - Current day: {today} (day_of_week={day_of_week})")

        if day_of_week == 0:  # Monday
            logger.debug(
                "  - Monday detected: fetching current week and next week releases"
            )
            current_releases = get_current_week_releases()
            next_releases = get_next_releases()

            message_parts = [":robot_face: *ROTA Release Reminder*\n"]

            if current_releases:
                logger.debug(
                    f"  - Adding current week section ({len(current_releases)} releases)"
                )
                message_parts.append(":threadparrot: *This week release*\n")
                message_parts.append(
                    format_release_message(current_releases, "This Week")
                )

            if next_releases:
                logger.debug(
                    f"  - Adding next week section ({len(next_releases)} releases)"
                )
                message_parts.append("\n:threadparrot: *Next release*\n")
                message_parts.append(format_release_message(next_releases, "Next Week"))

            if not current_releases and not next_releases:
                logger.debug("  - No releases found, adding empty state message")
                message_parts.append(
                    "No releases scheduled for this week or next week."
                )

            message = "\n".join(message_parts)

        elif day_of_week == 3:  # Thursday
            logger.debug(
                "  - Thursday detected: fetching current week releases (reminder)"
            )
            current_releases = get_current_week_releases()

            message_parts = [":robot_face: *ROTA Release Reminder (Mid-Week)*\n"]

            if current_releases:
                logger.debug(
                    f"  - Adding current week section ({len(current_releases)} releases)"
                )
                message_parts.append(
                    format_release_message(current_releases, "This Week")
                )
            else:
                logger.debug("  - No releases found, adding empty state message")
                message_parts.append("No releases scheduled for this week.")

            message = "\n".join(message_parts)
        else:
            logger.warning(
                f"  ✗ Group reminder triggered on unexpected day: {day_of_week}"
            )
            return

        if config.ROTA_GROUP_CHANNEL:
            logger.debug(f"  - Sending message to channel: {config.ROTA_GROUP_CHANNEL}")
            success = slack_client.send_message(
                channel=config.ROTA_GROUP_CHANNEL, text=message
            )

            if success:
                logger.info("  ✓ Group reminder sent successfully")
            else:
                logger.error("  ✗ Failed to send group reminder")
        else:
            logger.warning(
                "  ✗ ROTA_GROUP_CHANNEL not configured, skipping group reminder"
            )

    except Exception as e:
        logger.error(f"  ✗ Error in group reminder: {e}", exc_info=True)
        raise


def send_dm_reminders():
    """
    Send DM reminders to individuals about their releases

    Monday 9 AM: DMs for current week releases
    Friday 9 AM: DMs for next week releases only (if they exist)
    """
    logger.info("Step 4b: Sending DM reminders to individuals")

    try:
        today = datetime.now().date()
        day_of_week = today.weekday()  # 0 = Monday, 4 = Friday
        logger.debug(f"  - Current day: {today} (day_of_week={day_of_week})")

        if day_of_week == 0:  # Monday
            logger.debug("  - Monday detected: fetching current week releases for DM")
            releases = get_current_week_releases()
            week_label = "this week"

        elif day_of_week == 4:  # Friday
            logger.debug("  - Friday detected: fetching NEXT week releases for DM")
            releases = get_next_releases()
            week_label = "next week"

        else:
            logger.warning(
                f"  ✗ DM reminder triggered on unexpected day: {day_of_week}"
            )
            return

        if not releases:
            logger.info(f"  ✗ No releases for {week_label}, no DMs to send")
            return

        logger.debug(f"  - Building notification list for {len(releases)} release(s)")
        people_to_notify = {}

        for release in releases:
            pm = release.get("pm")
            if pm and pm != "TBD":
                user_id = config.ROTA_USERS.get(pm)
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
                    logger.debug(f"    • Added {pm} (PM) for {release.get('version')}")

            qe1 = release.get("qe1")
            if qe1 and qe1 != "TBD":
                user_id = config.ROTA_USERS.get(qe1)
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
                    logger.debug(
                        f"    • Added {qe1} (QE1) for {release.get('version')}"
                    )

            qe2 = release.get("qe2")
            if qe2 and qe2 != "TBD":
                user_id = config.ROTA_USERS.get(qe2)
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
                    logger.debug(
                        f"    • Added {qe2} (QE2) for {release.get('version')}"
                    )

        logger.debug(f"  - Sending DMs to {len(people_to_notify)} people")
        for user_id, user_info in people_to_notify.items():
            assignments = user_info.get("assignments", [])
            name = user_info.get("name", "Sustain-er")

            message_parts = [f":robot_face: Hey {name}!\n"]
            message_parts.append(
                "You're on ROTA this week! Here's what you're sustaining:\n"
            )

            for assignment in assignments:
                release = assignment["release"]
                role = assignment["role"]
                message_parts.append(f"Release *{release['version']}* - {role}\n")

            message_parts.append("Keep the builds running smoothly! :rocket:")
            message_parts.append("You've got this! :mechanical_arm:")

            message = "\n".join(message_parts)

            logger.debug(
                f"    - Sending DM to {name} ({user_id}) with {len(assignments)} assignment(s)"
            )
            success = slack_client.send_dm(user_id=user_id, text=message)

            if success:
                logger.info(f"  ✓ Sent DM reminder to {name} ({user_id})")
            else:
                logger.error(f"  ✗ Failed to send DM reminder to {name} ({user_id})")

        logger.info(f"  ✓ Completed DM reminders for {len(people_to_notify)} people")
    except Exception as e:
        logger.error(f"  ✗ Error in DM reminder: {e}", exc_info=True)
        raise


def send_rota_notifications():
    """
    Main ROTA notification job - combines group reminders and DM reminders

    Schedule:
    - Monday 9 AM: Group reminder (current week + next week if found) + DM reminders (current week only)
    - Thursday 9 AM: Group reminder only (same current week, mid-week recap)
    - Friday 9 AM: DM reminders only (next week releases if they exist)
    """
    logger.info("=" * 60)
    logger.info("STARTING ROTA NOTIFICATION JOB")
    logger.info("=" * 60)

    try:
        today = datetime.now().date()
        day_of_week = today.weekday()
        logger.info(f"Job started at {datetime.now()}")
        logger.info(f"Current date: {today}")

        if day_of_week == 0:  # Monday
            logger.info(
                "Monday 9 AM: Sending group reminder (current + next week if found) and DM reminders (current week)"
            )
            send_group_reminder()
            send_dm_reminders()

        elif day_of_week == 3:  # Thursday
            logger.info("Thursday 9 AM: Sending group reminder (current week) only")
            send_group_reminder()

        elif day_of_week == 4:  # Friday
            logger.info(
                "Friday 9 AM: Sending DM reminders (next week) only - skips if no next week releases"
            )
            send_dm_reminders()

        else:
            logger.info(f"Day {day_of_week}: No notifications scheduled")

        logger.info("=" * 60)
        logger.info("ROTA NOTIFICATION JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error("ROTA NOTIFICATION JOB FAILED")
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 60)
        raise
