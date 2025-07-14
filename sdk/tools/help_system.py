"""
Help system for the OCP Sustaining Bot.

This module provides a decorator-based help metadata system that allows
command handlers to store their help information alongside their implementation.
"""

import logging
from functools import wraps
from typing import Dict, List, Optional, Callable, Any, Union
from config import config

logger = logging.getLogger(__name__)

# Global command registry: command name -> function
COMMAND_REGISTRY: Dict[str, Callable] = {}


def command_meta(
    name: str,
    description: str,
    arguments: Optional[Dict[str, Dict[str, Any]]] = None,
    examples: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None,
):
    """
    Decorator to attach help metadata to command functions.

    Args:
        name: The command name (e.g., 'create-openstack-vm')
        description: Brief description of what the command does
        arguments: Dictionary with argument names as keys and argument info as values
        examples: List of example usage strings
        aliases: List of alternative command names

    Returns:
        Decorated function with help metadata attached
    """

    def decorator(func):
        # Store metadata on the function as attributes
        func._command_description = description
        func._command_arguments = arguments or {}
        func._command_examples = examples or []
        func._command_aliases = aliases or []

        # Register the command
        COMMAND_REGISTRY[name] = func

        # Register aliases
        if aliases:
            for alias in aliases:
                COMMAND_REGISTRY[alias] = func

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_dynamic_value(value_or_callable):
    """
    Get a value that might be static or callable.

    Args:
        value_or_callable: Either a static value or a callable that returns a value

    Returns:
        The resolved value
    """
    if callable(value_or_callable):
        try:
            return value_or_callable()
        except Exception as e:
            logger.error(f"Error getting dynamic value: {e}")
            return "<error getting value>"
    return value_or_callable


def get_openstack_os_names():
    """Get available OpenStack OS names from config."""
    try:
        return list(config.OS_IMAGE_MAP.keys())
    except Exception as e:
        logger.error(f"Error getting OpenStack OS names: {e}")
        return ["<error getting OS names>"]


def get_openstack_statuses():
    """Get valid OpenStack VM statuses."""
    return ["ACTIVE", "SHUTOFF", "ERROR"]


def get_aws_instance_states():
    """Get valid AWS instance states."""
    return ["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]


def get_aws_instance_types():
    """Get common AWS instance types."""
    return [
        "t2.micro",
        "t2.small",
        "t2.medium",
        "t3.micro",
        "t3.small",
        "t3.medium",
        "m5.large",
        "m5.xlarge",
    ]


def format_command_help(command_name: str, detailed: bool = False) -> str:
    """
    Format help text for a specific command.

    Args:
        command_name: Name of the command
        detailed: If True, include detailed argument descriptions

    Returns:
        Formatted help text
    """
    if command_name not in COMMAND_REGISTRY:
        return f"Command '{command_name}' not found."

    func = COMMAND_REGISTRY[command_name]

    # Basic format for command list
    if not detailed:
        description = getattr(func, "_command_description", "No description available")
        return f"`{command_name}` - {description}"

    # Detailed format for specific command help
    description = getattr(func, "_command_description", "No description available")
    arguments = getattr(func, "_command_arguments", {})
    examples = getattr(func, "_command_examples", [])
    aliases = getattr(func, "_command_aliases", [])

    help_text = [f"*{command_name}*", f"_{description}_", ""]

    # Add usage information
    if arguments:
        usage_parts = [command_name]
        for arg_name, arg_info in arguments.items():
            if arg_info.get("required", False):
                usage_parts.append(f"--{arg_name}=<{arg_name}>")
            else:
                usage_parts.append(f"[--{arg_name}=<{arg_name}>]")

        help_text.append(f"*Usage:* `{' '.join(usage_parts)}`")
        help_text.append("")

    # Add arguments section
    if arguments:
        help_text.append("*Arguments:*")
        for arg_name, arg_info in arguments.items():
            arg_line = f"  `--{arg_name}`"
            if arg_info.get("required", False):
                arg_line += " *(required)*"
            arg_line += f" - {arg_info.get('description', 'No description')}"

            # Add choices if available
            if "choices" in arg_info:
                choices = get_dynamic_value(arg_info["choices"])
                if choices and isinstance(choices, (list, tuple)):
                    if len(choices) > 10:
                        arg_line += f" (Options: {', '.join(str(c) for c in choices[:10])}, ...)"
                    else:
                        arg_line += f" (Options: {', '.join(str(c) for c in choices)})"

            # Add default value
            if "default" in arg_info:
                default_val = get_dynamic_value(arg_info["default"])
                arg_line += f" (Default: {default_val})"

            help_text.append(arg_line)
        help_text.append("")

    # Add examples
    if examples:
        help_text.append("*Examples:*")
        for example in examples:
            help_text.append(f"  `{example}`")
        help_text.append("")

    # Add aliases
    if aliases:
        help_text.append(f"*Aliases:* {', '.join(aliases)}")
        help_text.append("")

    return "\n".join(help_text).strip()


def handle_help_command(
    say, user: Optional[str] = None, command_name: Optional[str] = None
):
    """
    Handle help command requests.

    Args:
        say: Slack say function
        user: User requesting help
        command_name: Optional specific command to get help for
    """
    try:
        if command_name:
            # Show help for specific command
            if command_name in COMMAND_REGISTRY:
                help_text = format_command_help(command_name, detailed=True)
                greeting = f"Hello <@{user}>! " if user else "Hello! "
                say(f"{greeting}Here's help for `{command_name}`:\n\n{help_text}")
            else:
                # Suggest similar commands
                available_commands = list(COMMAND_REGISTRY.keys())
                suggestions = [
                    cmd
                    for cmd in available_commands
                    if command_name.lower() in cmd.lower()
                ]

                greeting = f"Hello <@{user}>! " if user else "Hello! "
                if suggestions:
                    say(
                        f"{greeting}Command `{command_name}` not found. Did you mean: {', '.join(suggestions[:5])}?"
                    )
                else:
                    say(
                        f"{greeting}Command `{command_name}` not found. Use `help` to see all available commands."
                    )
        else:
            # Show all commands
            greeting = f"Hello <@{user}>! " if user else "Hello! "
            help_text = [
                f"{greeting}Here's what I can help you with:\n",
                "*Available Commands:*",
            ]

            # Get unique commands (excluding aliases)
            unique_commands = {}
            for cmd_name, func in COMMAND_REGISTRY.items():
                if cmd_name not in unique_commands:
                    unique_commands[cmd_name] = func

            # Sort commands alphabetically
            sorted_commands = sorted(unique_commands.items())

            for cmd_name, func in sorted_commands:
                # Format command with arguments for display
                arguments = getattr(func, "_command_arguments", {})
                description = getattr(
                    func, "_command_description", "No description available"
                )

                # Build command usage string
                usage_parts = [cmd_name]
                for arg_name, arg_info in arguments.items():
                    if arg_info.get("required", False):
                        usage_parts.append(f"<{arg_name}>")
                    else:
                        usage_parts.append(f"[{arg_name}]")

                command_usage = " ".join(usage_parts)
                help_text.append(f"`{command_usage}` - {description}")

            help_text.extend(
                [
                    "",
                    "For detailed help on any command, use: `help <command-name>` or `<command-name> --help`",
                    "",
                    "Example: `help create-openstack-vm` or `create-openstack-vm --help`",
                ]
            )

            say("\n".join(help_text))

    except Exception as e:
        logger.error(f"Error in handle_help_command: {e}")
        greeting = f"Sorry <@{user}>, " if user else "Sorry, "
        say(f"{greeting}I encountered an error while generating help information.")


def register_command(name: str, handler: Callable, meta: Dict[str, Any]):
    """
    Manually register a command (for commands that can't use the decorator).

    Args:
        name: Command name
        handler: Handler function
        meta: Metadata dictionary
    """
    # Set attributes on the handler function
    handler._command_description = meta.get("description", "")
    handler._command_arguments = meta.get("arguments", {})
    handler._command_examples = meta.get("examples", [])
    handler._command_aliases = meta.get("aliases", [])

    # Register the command
    COMMAND_REGISTRY[name] = handler

    # Register aliases
    for alias in meta.get("aliases", []):
        COMMAND_REGISTRY[alias] = handler


def get_command_handler(command_name: str) -> Optional[Callable]:
    """
    Get the handler function for a command.

    Args:
        command_name: Name of the command

    Returns:
        Handler function or None if not found
    """
    if command_name in COMMAND_REGISTRY:
        return COMMAND_REGISTRY[command_name]
    return None


def list_commands() -> List[str]:
    """
    Get list of all registered command names.

    Returns:
        List of command names
    """
    return list(COMMAND_REGISTRY.keys())


def check_help_flag(params_dict: Dict[str, Any]) -> bool:
    """
    Check if the help flag is present in command parameters.

    Args:
        params_dict: Dictionary of command parameters

    Returns:
        True if help flag is present
    """
    return params_dict.get("help", False) or params_dict.get("h", False)
