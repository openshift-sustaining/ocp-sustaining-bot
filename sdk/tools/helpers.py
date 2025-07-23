import shlex
import logging
import re

from typing_extensions import Match

from sdk.tools.help_system import COMMAND_REGISTRY

logger = logging.getLogger(__name__)


def get_named_and_positional_params(command_line: str) -> tuple[dict, list]:
    """
    Parse command line arguments into a dictionary of parameters and their values and/or a list of parameters

    This function extracts command-line parameters from a string and converts them into
    a dictionary and list format. It handles both valued parameters (--key=value or --key value)
    and flag parameters (--flag). The function supports various parameter formats including
    comma-separated values and multi-token values.

    NB: if using a mixture of parameters and key/values, place the parameters before the key/values

    Args:
        command_line (str): The command line string to parse. Can include the command name
                           followed by parameters in various formats.

    Returns:
        tuple:
            dict: A dictionary containing parsed parameters where:
                  - Keys are parameter names (without leading dashes)
                  - Values are either:
                    * String values for parameters with values (comma-separated values are cleaned)
                    * Boolean True for flag parameters without values
                  - Returns empty dict {} if no parameters found or on parsing errors
            list: all parameters that don't start with -- or - will get added to the list

    Supported Parameter Formats:
        - --param=value          : {'param': 'value'}
        - --param value          : {'param': 'value'}
        - -param value           : {'param': 'value'}
        - --flag                 : {'flag': True}
        - --list=val1,val2       : {'list': 'val1,val2'}
        - --multi word value     : {'multi': 'word value'}
        - --quoted="spaced value": {'quoted': 'spaced value'}
        arg1 arg2

    Examples:
        >>> get_named_and_positional_params("aws vm list --type=t3.micro,t2.micro --state=pending,stopped --stop")
        {'type': 't3.micro,t2.micro', 'state': 'pending,stopped', 'stop': True}
        [""]

        >>> get_named_and_positional_params("command --region us-east-1 --verbose")
        {'region': 'us-east-1', 'verbose': True}
        [""]

        >>> get_named_and_positional_params("command --name 'my server' --count 5")
        {'name': 'my server', 'count': '5'}
        [""]

        >>> get_named_and_positional_params("command --list item1, item2 , item3")
        {'list': 'item1,item2,item3'}
        [""]

        >>> get_named_and_positional_params("")
        {}
        []

        >>> get_named_and_positional_params("command-with-no-params")
        {}
        [""]

        >>> get_named_and_positional_params("aws vm list param1 param2 --type=t3.micro,t2.micro --state=pending,stopped --stop", "aws vm list")
        {'type': 't3.micro,t2.micro', 'state': 'pending,stopped', 'stop': True}
        ['param1','param2']

    Notes:
        - Parameter names have leading dashes (-/--) stripped from keys
        - Comma-separated values are cleaned (extra whitespace removed)
        - Multi-token values are joined with spaces
        - Uses shlex.split for proper handling of quoted arguments
        - Gracefully handles malformed input by returning empty dict
        - Logs errors when parsing fails
        - Call get_list_of_values_for_key_in_dict_of_parameters to get a list of values for a key in the returned dictionary
    """
    if not isinstance(command_line, str):
        logger.error(f"command_line must be a string. command_line: {command_line}")
        return {}, []

    command_line = command_line.strip()
    if not command_line:
        return {}, []

    named_params = {}
    positional_params = []

    parameters_line = get_parameters_line(command_line)

    if not parameters_line:
        return {}, []

    try:
        # Use shlex.split to properly handle quoted arguments and spaces
        args = shlex.split(parameters_line)

        i = 0
        while i < len(args):
            token = args[i]

            # Handle both --param and -param formats
            if token.startswith("--") or (token.startswith("-") and len(token) > 1):
                # Extract the parameter name (remove leading dashes)
                key = token.lstrip("-")
                value = None

                if "=" in key:
                    # Handle --key=value format
                    key, value = key.split("=", 1)

                    # Check if this value continues across multiple tokens (comma-separated values)
                    value_parts = [value]
                    next_idx = i + 1

                    # Collect subsequent tokens until we hit another parameter or end of args
                    while (
                        next_idx < len(args)
                        and not args[next_idx].startswith("-")
                        and not args[next_idx].startswith("--")
                    ):
                        value_parts.append(args[next_idx])
                        next_idx += 1

                    # Join all value parts
                    value = " ".join(value_parts)
                    # Update index to skip the consumed tokens
                    i = next_idx - 1

                elif i + 1 < len(args) and not args[i + 1].startswith("-"):
                    # Handle --key value format
                    value_parts = [args[i + 1]]
                    next_idx = i + 2

                    # Collect subsequent tokens until we hit another parameter or end of args
                    while (
                        next_idx < len(args)
                        and not args[next_idx].startswith("-")
                        and not args[next_idx].startswith("--")
                    ):
                        value_parts.append(args[next_idx])
                        next_idx += 1

                    # Join all value parts
                    value = " ".join(value_parts)
                    # Update index to skip the consumed tokens
                    i = next_idx - 1

                # Clean up key name
                key = key.strip()

                # Only add valid parameter names
                if key:
                    if value is not None and value != "":
                        # Clean up comma-separated values in the value
                        cleaned_value = _clean_comma_separated_value(value)
                        named_params[key] = cleaned_value
                    else:
                        # Flag parameter without value (e.g., --stop, --delete)
                        named_params[key] = True
            # handle parameters that are not key/values
            elif len(token) > 1:
                positional_params.append(token.strip())
            i += 1

    except Exception as e:
        logger.error(f"Error parsing command line '{parameters_line}': {e}")

    return named_params, positional_params


def get_list_of_values_for_key_in_dict_of_parameters(
    key_name: str, dict_of_parameters: dict
) -> list[str]:
    """
    Given a dictionary of parameters and a key name, return a list of values for that key.

    Args:
        key_name: The parameter name to look for
        dict_of_parameters: Dictionary containing parameters and their values

    Returns:
        List of string values split by comma if the key exists and has a string value,
        empty list otherwise.

    Examples:
        >>> get_list_of_values_for_key_in_dict_of_parameters("state", {"state": "pending,stopped"})
        ['pending', 'stopped']
        >>> get_list_of_values_for_key_in_dict_of_parameters("missing", {"state": "pending"})
        []
        >>> get_list_of_values_for_key_in_dict_of_parameters("flag", {"flag": True})
        []
    """
    # Input validation
    if not key_name or not dict_of_parameters:
        return []

    if not isinstance(key_name, str) or not isinstance(dict_of_parameters, dict):
        return []

    # Get the value for the key
    value = dict_of_parameters.get(key_name)

    # Only process string values (skip booleans, None, etc.)
    if not isinstance(value, str) or not value.strip():
        return []

    # Use the existing comma-separated value cleaning function
    cleaned_value = _clean_comma_separated_value(value)

    # Split by comma and return the list
    return cleaned_value.split(",") if cleaned_value else []


def _clean_comma_separated_value(value: str) -> str:
    """
    Clean up comma-separated values by removing extra whitespace and empty values.
    E.g., "pending, stopped , running" -> "pending,stopped,running"
    """
    if not value or not isinstance(value, str):
        return value

    # Split by comma, strip each part, and filter out empty strings
    parts = [part.strip() for part in value.split(",") if part.strip()]

    # Join back with commas
    return ",".join(parts)


def _get_match_command_line(command_line: str) -> Match[str] | None:
    commands_pattern = "|".join(map(re.escape, COMMAND_REGISTRY))
    pattern = re.compile(
        r"^(?P<base_command>help$|"
        r"(?:(help\s)?"
        r"(" + commands_pattern + r")"
        r"(\s(?:help|h))?)"
        r")\b"
        r"(?P<params>.*)"
    )

    return pattern.match(command_line)


def get_base_command(command_line: str) -> str | None:
    """Extracts the base command."""
    match_command = _get_match_command_line(command_line)

    if not match_command:
        return None

    groups = match_command.groupdict()
    base_command = groups.get("base_command", "") or ""

    return f"{base_command}".strip()


def get_parameters_line(command_line: str) -> str | None:
    """Extracts the parameters line."""
    match_command = _get_match_command_line(command_line)

    if not match_command:
        return None

    groups = match_command.groupdict()
    params_line = groups.get("params", "") or ""

    return f"{params_line}".strip()


def remove_bot_username(command_line: str) -> str:
    """Remove the bot username from the command line."""
    cmd_strings = [x for x in command_line.split(" ") if x.strip() != ""]

    if len(cmd_strings) > 1 and (
        cmd_strings[0].startswith("<@") or cmd_strings[0].startswith("@")
    ):
        return " ".join(cmd_strings[1:])

    return " ".join(cmd_strings)


def validate_command(command_line: str) -> bool:
    """
    Validates the command line, returning True if the command is valid, False otherwise.
    """
    command_pattern = r"^\s*(\S.*?)(?:\s+--|$)"

    return bool(re.match(command_pattern, command_line))
