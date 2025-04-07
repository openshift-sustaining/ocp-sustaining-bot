from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
import re

from slack_helpers.helper_functions import (
    handle_help,
    handle_create_rosa_cluster,
    handle_create_openstack_vm,
    handle_hello,
    handle_create_aws_vm,
)

app = App(token=config.SLACK_BOT_TOKEN)


# Define the main event handler function
@app.event("app_mention")
@app.event("message")
def mention_handler(body, say):
    user = body.get("event", {}).get("user")
    text = body.get("event", {}).get("text", "").strip()

    # Create a command mapping
    commands = {
        r"\bhelp\b": lambda: handle_help(say, user),
        r"^create-rosa-cluster": lambda: handle_create_rosa_cluster(say, user, text),
        r"^create-openstack-vm": lambda: handle_create_openstack_vm(say, user, text),
        r"\bhello\b": lambda: handle_hello(say, user),
        r"\bcreate_aws_vm\b": lambda: handle_create_aws_vm(say, user),
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
