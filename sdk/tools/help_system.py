"""
Help system for the OCP Sustaining Bot.

This module provides a decorator-based help metadata system that allows
command handlers to store their help information alongside their implementation.
"""

import logging
from functools import wraps
from typing import Dict, List, Optional, Callable, Any
from config import config
import re

logger = logging.getLogger(__name__)

# Global command registry: command name -> function
COMMAND_REGISTRY: Dict[str, Callable] = {}

# Cached help text for performance
_CACHED_HELP_TEXT: Optional[str] = None


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
        name: The command name (e.g., 'openstack vm create')
        description: Brief description of what the command does
        arguments: Dictionary with argument names as keys and argument info as values
        examples: List of example usage strings
        aliases: List of alternative command names

    Returns:
        Decorated function with help metadata attached
    """

    def attach_metadata(func):
        # Store metadata on the function as attributes
        func._command_description = description
        func._command_arguments = arguments or {}
        func._command_examples = examples or []
        func._command_aliases = aliases or []

        # Register the command
        if name != "help":
            COMMAND_REGISTRY[name] = func

        # Register aliases
        if aliases:
            for alias in aliases:
                COMMAND_REGISTRY[alias] = func

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return attach_metadata


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


def get_aws_os_ami_names():
    """Get available AWS OS names from config."""
    try:
        aws_ami_map = getattr(config, "AWS_AMI_MAP", {"linux": "ami-0402e56c0a7afb78f"})
        return list(aws_ami_map.keys())
    except Exception as e:
        logger.error(f"Error getting AWS OS names: {e}")
        return ["<error getting OS names>"]


def get_openstack_statuses():
    """Get valid OpenStack VM statuses."""
    return ["ACTIVE", "SHUTOFF", "ERROR"]


def get_openstack_flavors():
    """Get common OpenStack flavors."""
    return [
        # Standard m1.* flavors
        "m1.tiny",
        "m1.small",
        "m1.medium",
        "m1.large",
        "m1.xlarge",
        # CI flavors
        "ci.cpu.small",
        "ci.cpu.medium",
        "ci.cpu.large",
        # General purpose flavors
        "t2.micro",
        "t2.small",
        "t2.medium",
        "t3.micro",
        "t3.small",
        "t3.medium",
        # Compute optimized flavors
        "c5.large",
        "c5.xlarge",
        "c5.2xlarge",
        # Memory optimized flavors
        "r5.large",
        "r5.xlarge",
        # Storage optimized flavors
        "i3.large",
        "i3.xlarge",
    ]


def get_gcp_os_names():
    """Get available GCP OS/image names from config."""
    try:
        gcp_image_map = getattr(
            config,
            "GCP_IMAGE_MAP",
            {
                "debian-12": "projects/debian-cloud/global/images/family/debian-12",
                "linux": "projects/debian-cloud/global/images/family/debian-12",
            },
        )
        return list(gcp_image_map.keys())
    except Exception as e:
        logger.error(f"Error getting GCP OS names: {e}")
        return ["<error getting OS names>"]


def get_gcp_instance_states():
    """Get valid GCP Compute Engine instance status values (lowercase, for filtering)."""
    return [
        "provisioning",  # Allocating resources
        "staging",       # Preparing for first boot
        "running",       # Booting or actively running
        "stopping",      # Shutting down
        "suspending",    # Being suspended
        "suspended",     # Suspended
        "repairing",     # Under repair
        "terminated",    # Stopped or deleted
    ]


def get_gcp_instance_types():
    """Return a complete list of GCP Compute Engine predefined machine types (general-purpose, compute-optimized, memory-optimized)."""
    return sorted([
        # E2 — cost-optimized general-purpose (shared-core + standard/highmem/highcpu)
        "e2-micro",
        "e2-small",
        "e2-medium",
        "e2-standard-2",
        "e2-standard-4",
        "e2-standard-8",
        "e2-standard-16",
        "e2-standard-32",
        "e2-highmem-2",
        "e2-highmem-4",
        "e2-highmem-8",
        "e2-highmem-16",
        "e2-highcpu-2",
        "e2-highcpu-4",
        "e2-highcpu-8",
        "e2-highcpu-16",
        "e2-highcpu-32",
        # N1 — legacy general-purpose (shared-core + standard/highmem/highcpu)
        "f1-micro",
        "g1-small",
        "n1-standard-1",
        "n1-standard-2",
        "n1-standard-4",
        "n1-standard-8",
        "n1-standard-16",
        "n1-standard-32",
        "n1-standard-64",
        "n1-standard-96",
        "n1-highmem-2",
        "n1-highmem-4",
        "n1-highmem-8",
        "n1-highmem-16",
        "n1-highmem-32",
        "n1-highmem-64",
        "n1-highmem-96",
        "n1-highcpu-2",
        "n1-highcpu-4",
        "n1-highcpu-8",
        "n1-highcpu-16",
        "n1-highcpu-32",
        "n1-highcpu-64",
        "n1-highcpu-96",
        # N2 — Intel general-purpose
        "n2-standard-2",
        "n2-standard-4",
        "n2-standard-8",
        "n2-standard-16",
        "n2-standard-32",
        "n2-standard-64",
        "n2-standard-80",
        "n2-standard-128",
        "n2-highmem-2",
        "n2-highmem-4",
        "n2-highmem-8",
        "n2-highmem-16",
        "n2-highmem-32",
        "n2-highmem-64",
        "n2-highmem-80",
        "n2-highmem-128",
        "n2-highcpu-2",
        "n2-highcpu-4",
        "n2-highcpu-8",
        "n2-highcpu-16",
        "n2-highcpu-32",
        "n2-highcpu-64",
        "n2-highcpu-80",
        "n2-highcpu-128",
        # N2D — AMD general-purpose
        "n2d-standard-2",
        "n2d-standard-4",
        "n2d-standard-8",
        "n2d-standard-16",
        "n2d-standard-32",
        "n2d-standard-48",
        "n2d-standard-64",
        "n2d-standard-80",
        "n2d-standard-96",
        "n2d-standard-128",
        "n2d-standard-224",
        "n2d-highmem-2",
        "n2d-highmem-4",
        "n2d-highmem-8",
        "n2d-highmem-16",
        "n2d-highmem-32",
        "n2d-highmem-48",
        "n2d-highmem-64",
        "n2d-highmem-80",
        "n2d-highmem-96",
        "n2d-highmem-128",
        "n2d-highmem-224",
        "n2d-highcpu-2",
        "n2d-highcpu-4",
        "n2d-highcpu-8",
        "n2d-highcpu-16",
        "n2d-highcpu-32",
        "n2d-highcpu-48",
        "n2d-highcpu-64",
        "n2d-highcpu-80",
        "n2d-highcpu-96",
        "n2d-highcpu-128",
        "n2d-highcpu-224",
        # Tau T2D — AMD scale-out
        "t2d-standard-1",
        "t2d-standard-2",
        "t2d-standard-4",
        "t2d-standard-8",
        "t2d-standard-16",
        "t2d-standard-32",
        "t2d-standard-48",
        "t2d-standard-60",
        "t2d-highmem-2",
        "t2d-highmem-4",
        "t2d-highmem-8",
        "t2d-highmem-16",
        "t2d-highmem-32",
        "t2d-highmem-48",
        "t2d-highcpu-2",
        "t2d-highcpu-4",
        "t2d-highcpu-8",
        "t2d-highcpu-16",
        "t2d-highcpu-32",
        "t2d-highcpu-48",
        "t2d-highcpu-60",
        # Tau T2A — Arm (Ampere)
        "t2a-standard-1",
        "t2a-standard-2",
        "t2a-standard-4",
        "t2a-standard-8",
        "t2a-standard-16",
        "t2a-standard-32",
        "t2a-standard-48",
        "t2a-highmem-2",
        "t2a-highmem-4",
        "t2a-highmem-8",
        "t2a-highmem-16",
        "t2a-highmem-32",
        "t2a-highmem-48",
        "t2a-highcpu-2",
        "t2a-highcpu-4",
        "t2a-highcpu-8",
        "t2a-highcpu-16",
        "t2a-highcpu-32",
        "t2a-highcpu-48",
        # C2 — compute-optimized (Intel)
        "c2-standard-4",
        "c2-standard-8",
        "c2-standard-16",
        "c2-standard-30",
        "c2-standard-60",
        # C2D — compute-optimized (AMD)
        "c2d-standard-2",
        "c2d-standard-4",
        "c2d-standard-8",
        "c2d-standard-16",
        "c2d-standard-32",
        "c2d-standard-56",
        "c2d-standard-112",
        "c2d-highmem-2",
        "c2d-highmem-4",
        "c2d-highmem-8",
        "c2d-highmem-16",
        "c2d-highmem-32",
        "c2d-highmem-56",
        "c2d-highmem-112",
        "c2d-highcpu-2",
        "c2d-highcpu-4",
        "c2d-highcpu-8",
        "c2d-highcpu-16",
        "c2d-highcpu-32",
        "c2d-highcpu-56",
        "c2d-highcpu-112",
        # C3 — compute-optimized (Intel, newer)
        "c3-standard-4",
        "c3-standard-8",
        "c3-standard-22",
        "c3-standard-44",
        "c3-standard-88",
        "c3-standard-176",
        "c3-highmem-4",
        "c3-highmem-8",
        "c3-highmem-22",
        "c3-highmem-44",
        "c3-highmem-88",
        "c3-highmem-176",
        "c3-highcpu-4",
        "c3-highcpu-8",
        "c3-highcpu-22",
        "c3-highcpu-44",
        "c3-highcpu-88",
        "c3-highcpu-176",
        # C3D — compute-optimized (AMD)
        "c3d-standard-4",
        "c3d-standard-8",
        "c3d-standard-22",
        "c3d-standard-44",
        "c3d-standard-88",
        "c3d-standard-176",
        "c3d-highmem-4",
        "c3d-highmem-8",
        "c3d-highmem-22",
        "c3d-highmem-44",
        "c3d-highmem-88",
        "c3d-highmem-176",
        "c3d-highmem-360",
        "c3d-highcpu-4",
        "c3d-highcpu-8",
        "c3d-highcpu-22",
        "c3d-highcpu-44",
        "c3d-highcpu-88",
        "c3d-highcpu-176",
        # N4 — general-purpose 4th gen (Intel)
        "n4-standard-2",
        "n4-standard-4",
        "n4-standard-8",
        "n4-standard-16",
        "n4-standard-32",
        "n4-standard-64",
        "n4-standard-80",
        "n4-highmem-2",
        "n4-highmem-4",
        "n4-highmem-8",
        "n4-highmem-16",
        "n4-highmem-32",
        "n4-highmem-64",
        "n4-highmem-80",
        "n4-highcpu-2",
        "n4-highcpu-4",
        "n4-highcpu-8",
        "n4-highcpu-16",
        "n4-highcpu-32",
        "n4-highcpu-64",
        "n4-highcpu-80",
        # N4D — general-purpose 4th gen (AMD)
        "n4d-standard-2",
        "n4d-standard-4",
        "n4d-standard-8",
        "n4d-standard-16",
        "n4d-standard-32",
        "n4d-standard-64",
        "n4d-standard-96",
        "n4d-highmem-2",
        "n4d-highmem-4",
        "n4d-highmem-8",
        "n4d-highmem-16",
        "n4d-highmem-32",
        "n4d-highmem-64",
        "n4d-highmem-96",
        "n4d-highcpu-2",
        "n4d-highcpu-4",
        "n4d-highcpu-8",
        "n4d-highcpu-16",
        "n4d-highcpu-32",
        "n4d-highcpu-64",
        "n4d-highcpu-96",
        # M1 — memory-optimized (legacy)
        "m1-megamem-96",
        "m1-ultramem-40",
        "m1-ultramem-80",
        "m1-ultramem-160",
        "m1-highmem-4",
        "m1-highmem-8",
        "m1-highmem-16",
        "m1-highmem-32",
        "m1-highmem-64",
        "m1-highmem-96",
        "m1-highmem-160",
        # M2 — memory-optimized (large memory)
        "m2-megamem-416",
        "m2-ultramem-208",
        "m2-ultramem-416",
        "m2-highmem-416",
        # M3 — memory-optimized
        "m3-standard-8",
        "m3-standard-16",
        "m3-standard-32",
        "m3-standard-64",
        "m3-standard-128",
        "m3-highmem-8",
        "m3-highmem-16",
        "m3-highmem-32",
        "m3-highmem-64",
        "m3-highmem-128",
        "m3-megamem-64",
        "m3-megamem-128",
        "m3-ultramem-32",
        "m3-ultramem-64",
        "m3-ultramem-128",
        # M4 — memory-optimized (newer)
        "m4-standard-8",
        "m4-standard-16",
        "m4-standard-32",
        "m4-standard-64",
        "m4-standard-96",
        "m4-standard-128",
        "m4-standard-192",
        "m4-standard-224",
        "m4-highmem-8",
        "m4-highmem-16",
        "m4-highmem-32",
        "m4-highmem-64",
        "m4-highmem-96",
        "m4-highmem-128",
        "m4-highmem-192",
        "m4-highmem-224",
        "m4-megamem-16",
        "m4-megamem-32",
        "m4-megamem-64",
        "m4-megamem-96",
        "m4-megamem-128",
        "m4-megamem-192",
        "m4-megamem-224",
        "m4-ultramem-32",
        "m4-ultramem-64",
        "m4-ultramem-96",
        "m4-ultramem-128",
        "m4-ultramem-192",
        "m4-ultramem-224",
        # H3 — compute-optimized HPC
        "h3-standard-88",
        # H4D — compute-optimized HPC (AMD)
        "h4d-standard-192",
    ])


def get_aws_instance_states():
    """Get valid AWS instance states."""
    return ["pending", "running", "shutting-down", "terminated", "stopping", "stopped"]


def get_aws_instance_types():
    """Get common AWS instance types."""
    # TODO: Confirm with team before expanding to include m5 instances
    return [
        "t2.micro",
        "t2.small",
        "t2.medium",
        "t3.micro",
        "t3.small",
        "t3.medium",
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


def _build_general_help_text() -> str:
    """
    Build the general help text with all commands.
    This is cached for performance since commands don't change after startup.
    """
    help_lines = ["*Available Commands:*"]

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
        description = getattr(func, "_command_description", "No description available")

        # Build command usage string
        usage_parts = [cmd_name]
        for arg_name, arg_info in arguments.items():
            if arg_info.get("required", False):
                usage_parts.append(f"<{arg_name}>")
            else:
                usage_parts.append(f"[{arg_name}]")

        command_usage = " ".join(usage_parts)
        help_lines.append(f"`{command_usage}` - {description}")

    help_lines.extend(
        [
            "",
            "For detailed help on any command, use: `help <command-name>` or `<command-name> --help`",
            "",
            "Example: `help openstack vm create` or `openstack vm create --help`",
        ]
    )

    return "\n".join(help_lines)


def get_cached_general_help() -> str:
    """
    Get cached general help text, building it if not already cached.
    """
    global _CACHED_HELP_TEXT
    if _CACHED_HELP_TEXT is None:
        _CACHED_HELP_TEXT = _build_general_help_text()
    return _CACHED_HELP_TEXT


def remove_help_from_command(command_name) -> str:
    """
    Remove help from command.
    """
    if command_name and check_help_flag(command_name):
        return command_name.replace("help ", "").replace(" help", "").replace(" h", "")

    return command_name


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
            command_name = remove_help_from_command(command_name)

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
            # Show all commands using cached help text
            greeting = f"Hello <@{user}>! " if user else "Hello! "
            cached_help = get_cached_general_help()
            say(f"{greeting}Here's what I can help you with:\n\n{cached_help}")

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


def check_help_flag(command_line) -> bool:
    """
    Check if the help flag is present in command line.

    Args:
        command_line: string

    Returns:
        True if help flag is present, False otherwise
    """
    help_pattern = re.compile(r"^help\b\s.+|.*\S.*\s(-{0,2}h(elp)?)$")
    return bool(help_pattern.match(command_line))
