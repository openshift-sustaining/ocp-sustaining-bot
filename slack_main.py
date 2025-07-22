from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
from sdk.tools.helpers import process_command_parameters
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
)

logger = logging.getLogger(__name__)

app = App(token=config.SLACK_BOT_TOKEN)

try:
    ALLOWED_SLACK_USERS = config.ALLOWED_SLACK_USERS
except json.JSONDecodeError:
    logging.error("ALLOWED_SLACK_USERS must be a valid JSON string.")
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

    cmd_strings = [x for x in command_line.split(" ") if x.strip() != ""]
    if len(cmd_strings) > 0:
        if cmd_strings[0][:2] == "<@" and len(cmd_strings) > 1:
            # Can't filter based on `app.event` since mentioning bot in DM
            # is classified as `message` not as `app_mention`, so we remove
            # the `@ocp-sustaining-bot` part
            cmd = cmd_strings[1].lower()
            command_line = " ".join(cmd_strings[1:])
        else:
            cmd = cmd_strings[0]
            command_line = " ".join(cmd_strings)

        # Extract parameters using the utility function
        params_dict, list_params = process_command_parameters(command_line)

        # Check if this is a help request for a specific command
        if check_help_flag(params_dict):
            handle_help_command(say, user, cmd)
            return

        # Check if this is a help request (with or without specific command)
        if cmd == "help":
            # Extract the target command name from the command line
            # Handle both "@bot help command" and "help command" formats
            words = command_line.split()
            if len(words) > 1:
                command_name = words[1].lower()
                handle_help_command(say, user, command_name)
            else:
                # Just "help" - show all commands
                handle_help_command(say, user)
            return

        # Command routing
        commands = {
            "create-openstack-vm": lambda: handle_create_openstack_vm(
                say, user, app, params_dict
            ),
            "list-openstack-vms": lambda: handle_list_openstack_vms(say, params_dict),
            "hello": lambda: handle_hello(say, user),
            "create-aws-vm": lambda: handle_create_aws_vm(
                say,
                user,
                region,
                app,  # pass `app` so that bot can send DM to users
                params_dict,
            ),
            "aws-modify-vm": lambda: handle_aws_modify_vm(
                say, region, user, params_dict
            ),
            "list-aws-vms": lambda: handle_list_aws_vms(say, region, user, params_dict),
            "list-team-links": lambda: handle_list_team_links(say, user),
        }

        try:
            commands[cmd]()
            return
        except KeyError:
            # Invalid command, will revert to error message
            pass

    # If no match is found, provide a default message
    say(
        f"Hello <@{user}>! I couldn't understand your request. Please try again or type 'help' for assistance."
    )


# Main Entry Point
if __name__ == "__main__":
    logger.info("Starting Slack bot...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
