from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
from sdk.tools.helpers import get_dict_of_command_parameters
import logging
import json
import sys
import os

from slack_handlers.handlers import (
    handle_help,
    handle_create_openstack_vm,
    handle_list_openstack_vms,
    handle_hello,
    handle_create_aws_vm,
    handle_list_aws_vms,
    handle_list_team_links,
    handle_aws_modify_vm,
)

def setup_logging():
    """Configure logging for the application."""
    log_level = getattr(config, 'LOG_LEVEL', 'INFO').upper()
    is_running_as_docker = os.getenv('DOCKER_CONTAINER') or os.path.exists('/.dockerenv')
    
    # Convert string level to numeric level
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Force stdout logging in Docker containers
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout if is_running_as_docker else None,
        force=True
    )
    
    # Get logger instance
    logger_instance = logging.getLogger(__name__)
    
    # Debug information to help troubleshoot
    # print(f"DEBUG: Configured log level: {log_level} (numeric: {numeric_level})")
    # print(f"DEBUG: Running in Docker: {is_running_as_docker}")
    # print(f"DEBUG: Logger handlers: {logging.getLogger().handlers}")
    
    return logger_instance


# Set up logging early
logger = setup_logging()
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
        params_dict = get_dict_of_command_parameters(command_line)

        commands = {
            "help": lambda: handle_help(say, user),
            "create-openstack-vm": lambda: handle_create_openstack_vm(
                say, user, params_dict
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
    logger.info("Starting Slack bot with Socket Mode handler...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
