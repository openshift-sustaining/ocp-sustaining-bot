from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
from sdk.tools.helpers import (
    get_named_and_positional_params,
    validate_command,
    remove_bot_username,
    get_base_command,
)
from sdk.tools.help_system import handle_help_command, check_help_flag
import logging
import json
import sys

from slack_handlers.handlers import (
    handle_create_openstack_vm,
    handle_list_openstack_vms,
    handle_hello,
    handle_create_aws_vm,
    handle_list_aws_vms,
    handle_list_team_links,
    handle_aws_modify_vm,
    handle_openstack_modify_vm,
)

logger = logging.getLogger(__name__)

app = App(token=config.SLACK_BOT_TOKEN)

try:
    ALLOWED_SLACK_USERS = config.ALLOWED_SLACK_USERS
except json.JSONDecodeError:
    logger.error("ALLOWED_SLACK_USERS must be a valid JSON string.")
    sys.exit(1)


def is_user_allowed(user_id: str) -> bool:
    return user_id in ALLOWED_SLACK_USERS.values()


# Define the main event handler function
@app.event("app_mention")
@app.event("message")
def mention_handler(body, say):
    user = body.get("event", {}).get("user")

    # Authorization check
    if config.ALLOW_ALL_WORKSPACE_USERS:
        if not is_user_allowed(user):
            say(
                f"Sorry <@{user}>, you're not authorized to use this bot.Contact ocp-sustaining-admin@redhat.com for assistance."
            )
            return

    command_line = body.get("event", {}).get("text", "").strip()
    region = config.AWS_DEFAULT_REGION

    if not validate_command(command_line):
        say(
            f"Hello <@{user}>! I couldn't understand your request. Please try again or type 'help' for assistance."
        )
        return

    command_line = remove_bot_username(command_line)

    base_command = get_base_command(command_line)

    # Extract parameters using the utility function
    named_params, positional_params = get_named_and_positional_params(command_line)

    # Check if this is a help request for a specific command
    if check_help_flag(command_line):
        handle_help_command(say, user, base_command)
        return

    commands = {
        "openstack vm create": lambda: handle_create_openstack_vm(
            say, user, app, named_params
        ),
        "openstack vm list": lambda: handle_list_openstack_vms(say, named_params),
        "openstack vm modify": lambda: handle_openstack_modify_vm(
            say, user, named_params
        ),
        "hello": lambda: handle_hello(say, user),
        "aws vm create": lambda: handle_create_aws_vm(
            say,
            user,
            region,
            app,  # pass `app` so that bot can send DM to users
            named_params,
        ),
        "aws vm modify": lambda: handle_aws_modify_vm(say, region, user, named_params),
        "aws vm list": lambda: handle_list_aws_vms(say, region, user, named_params),
        "project links list": lambda: handle_list_team_links(say, user),
        "help": lambda: handle_help_command(say, user),
    }

    command_function = commands.get(base_command)

    if not command_function:
        say(
            f"Hello <@{user}>! I couldn't understand your request. Please try again or type 'help' for assistance."
        )
        return

    try:
        command_function()
    except Exception as e:
        logger.error(f"An error occurred and it was caught at the mention_handler: {e}")
        say("An internal error occurred, please contact administrator.")


# Main Entry Point
if __name__ == "__main__":
    logger.info("Starting Slack bot...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
