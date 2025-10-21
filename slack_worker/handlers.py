from config import config
from sdk.tools.help_system import (
    command_meta,
    handle_help_command,
    get_openstack_os_names,
    get_openstack_statuses,
    get_openstack_flavors,
    get_aws_instance_states,
    get_aws_instance_types,
)
from slack_worker.gsheet.gsheet import gsheet 
import logging
import traceback
import functools
from datetime import datetime


logger = logging.getLogger(__name__)


# Helper function to handle ROTA operations
@command_meta(
    name="rota",
    description="Manage release rotation assignments in Google Sheets",
    arguments={
        "action": {
            "description": "Action to perform",
            "required": True,
            "type": "str",
            "choices": ["add", "check", "replace"],
        },
        "release": {
            "description": "Release version (e.g., 4.15.1)",
            "required": False,
            "type": "str",
        },
        "start": {
            "description": "Start date in YYYY-MM-DD format (must be a Monday)",
            "required": False,
            "type": "str",
        },
        "end": {
            "description": "End date in YYYY-MM-DD format (must be a Friday)",
            "required": False,
            "type": "str",
        },
        "pm": {
            "description": "Project Manager username",
            "required": False,
            "type": "str",
        },
        "qe1": {
            "description": "Primary QE engineer username",
            "required": False,
            "type": "str",
        },
        "qe2": {
            "description": "Secondary QE engineer username",
            "required": False,
            "type": "str",
        },
    },
    examples=[
        "rota --add --release=4.15.1 [--start=2024-01-08 --end=2024-01-12 --pm=john.doe --qe1=jane.smith --qe2=bob.wilson]",
        "rota --check --time='This Week'",
        "rota --check --release=4.15.1"
        "rota --replace --release=4.15.1 --column=new_pm [--user=new_person]",
    ],
)
def handle_rota(say, user, params_dict):
    """
    Function to interface with ROTA sheet.
    `add` will add a new release
    `check` will return the details of a release either by version or by time period (`This Week` or `Next Week`)
    `replace` will replace a user with someone else
    """
    if [
        params_dict.get("add"),
        params_dict.get("check"),
        params_dict.get("replace"),
    ].count(True) > 1:
        say("You can use only 1 of `add`, `check` and `replace`")
        return

    # Add
    if params_dict.get("add"):
        if user not in config.ROTA_ADMINS.values():
            say("Sorry. Only admins can add releases.")
            return

        rel_ver = params_dict.get("release")
        if not rel_ver:
            say("Please provide a release.")
            return

        try:
            start = params_dict.get("start")
            end = params_dict.get("end")

            error = (
                _helper_date_validation(start, 0)
                + "\n"
                + _helper_date_validation(end, 4)
                + "\n"
                + _helper_date_cmp(start, end)
            )
            error = error.strip()
            if error:
                say(error)
                return

            gsheet.add_release(
                rel_ver,
                s_date=start,
                e_date=end,
                pm=_get_name_from_userid(params_dict.get("pm")),
                qe1=_get_name_from_userid(params_dict.get("qe1")),
                qe2=_get_name_from_userid(params_dict.get("qe2")),
            )
        except ValueError as e:
            say(str(e))
            return

        say("Success!")
        return

    elif params_dict.get("check"):
        rel_ver = params_dict.get("release")
        time_period = params_dict.get("time")

        if rel_ver and time_period:
            say("Only provide one of `release` and `time`.")
            return

        elif rel_ver:
            try:
                data = gsheet.fetch_data_by_release(rel_ver)
            except ValueError:
                say("Please provide a correctly formatted release version.")
                return

        elif time_period:
            try:
                data = gsheet.fetch_data_by_time(time_period)
            except ValueError:
                say("Time period should either be `This Week` or `Next Week`.")
                return

        else:
            say("Please provide either `release` or `time`.")
            return

        if not data:
            say("Sorry, could not find the requested data.")
            return

        logger.debug(f"Received data from sheet: {data}")

        if isinstance(data[0], list):
            formatted_str = "\n\n".join(_helper_format_rota_output(d) for d in data)
        else:
            formatted_str = _helper_format_rota_output(data)

        formatted_str = (
            formatted_str.strip() or "Sorry, could not find the requested data."
        )

        say(formatted_str)
        return

    elif params_dict.get("replace"):
        if user not in config.ROTA_USERS.values():
            say("You are not authorized to use `replace`.")
            return

        rel_ver = params_dict.get("release")
        column = params_dict.get("column")
        user = _get_name_from_userid(params_dict.get("user"))

        if not all([rel_ver, column]):
            say("Please provide `release` and `column`.")
            return

        try:
            gsheet.replace_user_for_release(rel_ver, column, user)
        except ValueError as e:
            say(e)

        say("Success!")
        return

    else:
        say("You need one of `add`, `check` or `replace`.")
        return


def _helper_format_rota_output(data: list) -> str:
    if not data or len(data) != 7:
        logger.error(f"Cannot format ROTA data: {data}")
        return "Some error occurred parsing the data."

    rel_ver, s_date, e_date, pm, qe1, qe2, activity = data

    if rel_ver == "N/A":
        return ""

    pm = _get_userid_from_name(pm)
    qe1 = _get_userid_from_name(qe1)
    qe2 = _get_userid_from_name(qe2)

    return (
        f"*Release:* {rel_ver}\n" + f"*Patch Manager:* {pm}\n" + f"*QE:* {qe1}, {qe2}"
    )


def _get_userid_from_name(name: str) -> str:
    return f"<@{config.ROTA_USERS.get(name, name)}>"


def _get_name_from_userid(userid: str) -> str:
    if not userid:
        return

    if not userid.startswith("<@") or not userid.endswith(">"):
        return userid

    userid = userid[2:-1]

    @functools.cache
    def reverse_dict():
        return {v: k for k, v in config.ROTA_USERS.items()}

    rev_dict = reverse_dict()
    return rev_dict.get(userid, userid)


def _helper_date_validation(date: str, day: int) -> str:
    # Return empty string for correct date
    if not date:
        return ""
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Please format the date in the format YYYY-MM-DD."

    if not d:
        return "Something went wrong while parsing date."

    if d.weekday() != day:
        if day == 0:
            return "Start date should be a Monday."
        elif day == 4:
            return "End date should be a Friday."
        else:
            return "Day of the week is incorrect"

    return ""


def _helper_date_cmp(start: str, end: str) -> str:
    # Validate that start date is before end date
    try:
        s_date = datetime.strptime(start, "%Y-%m-%d")
        e_date = datetime.strptime(end, "%Y-%m-%d")

        if s_date >= e_date:
            return "End date should be after start date."
        else:
            return ""
    except ValueError:
        return ""
    

#Posts a formatted summary of releases for a given time period ("This Week" or "Next Week") into a Slack channel.
def _post_rota_summary(say, period: str):
    try:
        data = gsheet.fetch_data_by_time(period)
    except ValueError as e:
        logger.error(f"Invalid period for rota summary: {e}")
        return

    if not data:
        say(f"No releases found for *{period}*.")
        return

    header = f"*📢 {period}'s Releases:*"
    formatted = "\n\n".join(_helper_format_rota_output(d) for d in data)
    message = f"{header}\n\n{formatted}"

    say(message)
    logger.info(f"Posted {period} release summary to group.")


# Sends direct messages (DMs) to people assigned to a release in the given period
def _dm_rota_participants(say, period: str):
    try:
        data = gsheet.fetch_data_by_time(period)
    except ValueError as e:
        logger.error(f"Invalid period for rota DMs: {e}")
        return

    if not data:
        logger.info(f"No releases found for {period}, skipping DMs.")
        return

    sent = set()
    for row in data:
        if len(row) != 7:
            continue
        rel_ver, s_date, e_date, pm, qe1, qe2, _ = row

        for name in (pm, qe1, qe2):
            if not name or name in sent:
                continue
            sent.add(name)

            slack_id = config.ROTA_USERS.get(name)
            if not slack_id:
                logger.warning(f"No Slack ID for {name}. Skipping.")
                continue

            msg = (
                f" Hi <@{slack_id}>! Reminder: You’re assigned to *{rel_ver}* "
                f"({period}).\nDates: {s_date or '?'} → {e_date or '?'}"
            )
            say(msg, channel=slack_id)

    logger.info(f"Sent {len(sent)} DM reminders for {period}.")


def handle_rota_reminders(say):
    """
    Automatically post and DM ROTA reminders.

    - Monday: Post this week's releases to group & DM participants.
    - Thursday: Post this week's releases to group.
    - Friday: DM next week's participants on that release.
    """

    today = datetime.date.today()
    weekday = today.weekday()  # Monday = 0, Thursday = 3, Friday = 4

    if not gsheet:
        logger.error("GSheet not initialized.")
        return

    if weekday == 0:
        # Monday
        _post_rota_summary(say, "This Week")
        _dm_rota_participants(say, "This Week")

    elif weekday == 3:
        # Thursday
        _post_rota_summary(say, "This Week")

    elif weekday == 4:
        # Friday
        _dm_rota_participants(say, "Next Week")

    else:
        logger.info(f"No ROTA reminder scheduled for weekday {weekday}.")
