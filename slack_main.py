from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
import re
import logging

from slack_handlers.handlers import (
    handle_help,
    handle_create_openstack_vm,
    handle_list_openstack_vms,
    handle_hello,
    handle_create_aws_vm,
    handle_list_aws_vms,
)

logger = logging.getLogger(__name__)

app = App(token=config.SLACK_BOT_TOKEN)


# Define the main event handler function
@app.event("app_mention")
@app.event("message")
def mention_handler(body, say):
    user = body.get("event", {}).get("user")
    command_line = body.get("event", {}).get("text", "").strip()
    region = config.AWS_DEFAULT_REGION

    cmd_strings = [x for x in command_line.split(" ") if x.strip() != ""]
    if len(cmd_strings) > 0:
        if cmd_strings[0][:2] == "<@":
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
                say, user, region, command_line
            ),
            "list-aws-vm": lambda: handle_list_aws_vms(say, region, user, command_line),
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
