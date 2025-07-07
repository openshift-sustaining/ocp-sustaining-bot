from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
import logging
import json
import sys

from slack_handlers.handlers import (
    handle_help,
    handle_create_openstack_vm,
    handle_list_openstack_vms,
    handle_hello,
    handle_create_aws_vm,
    handle_list_aws_vms,
    handle_list_team_links,
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

        commands = {
            "help": lambda: handle_help(say, user),
            "create-openstack-vm": lambda: handle_create_openstack_vm(
                say, user, command_line
            ),
            "list-openstack-vms": lambda: handle_list_openstack_vms(say, command_line),
            "hello": lambda: handle_hello(say, user),
            "create-aws-vm": lambda: handle_create_aws_vm(
                say,
                user,
                region,
                command_line,
                app,  # pass `app` so that bot can send DM to users
            ),
            "list-aws-vms": lambda: handle_list_aws_vms(
                say, region, user, command_line
            ),
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
