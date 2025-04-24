from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
import re

from slack_handlers.handlers import (
    handle_help,
    handle_create_openstack_vm,
    handle_list_openstack_vms,
    handle_hello,
    handle_create_aws_vm,
    handle_list_aws_vms,
)

app = App(token=config.SLACK_BOT_TOKEN)


# Define the main event handler function
@app.event("app_mention")
@app.event("message")
def mention_handler(body, say):
    user = body.get("event", {}).get("user")
    text = body.get("event", {}).get("text", "").strip()
    region = config.AWS_DEFAULT_REGION

    cmd_strings = text.split(" ")
    if len(cmd_strings) > 0:
        first_command = cmd_strings[0]
        if first_command[:2] == "<@":
            # remove the @ocp-sustaining-bot part from the text - it will have a value like '<@U08JUNY7PD4>'
            cmd_strings.pop(0)
        # remove any empty strings which will be there if there were > 1 spaces between parameters
        valid_cmd_strings = [
            sub_string for sub_string in cmd_strings if sub_string != ""
        ]
        text = " ".join(valid_cmd_strings)
        # Create a command mapping
        commands = {
            r"\bhelp\b": lambda: handle_help(say, user),
            r"^create-openstack-vm": lambda: handle_create_openstack_vm(
                say, user, text
            ),
            r"\blist-openstack-vms\b": lambda: handle_list_openstack_vms(say),
            r"\bhello\b": lambda: handle_hello(say, user),
            r"\bcreate-aws-vm\b": lambda: handle_create_aws_vm(say, user, region),
            r"\blist-aws-vms\b": lambda: handle_list_aws_vms(say, region),
        }

        # Check for command matches and execute the appropriate handler
        for pattern, handler in commands.items():
            if re.search(pattern, text, re.IGNORECASE):
                handler()  # Execute the handler
                return

    # If no match is found, provide a default message
    say(
        f"Hello <@{user}>! I couldn't understand your request. Please try again or type 'help' for assistance."
    )


# Main Entry Point
if __name__ == "__main__":
    print("Starting Slack bot...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
