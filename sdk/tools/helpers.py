import shlex
import logging

logger = logging.getLogger(__name__)


def get_dict_of_command_parameters(command_line: str) -> dict:
    """
    Given the command_line e.g. list-aws-vms --type=t3.micro,t2.micro --state=pending,stopped
    Parse the parameters and return a dictionary of parameters and a list of associated values if present else {}
       For example, {'state': 'pending,stopped', 'type': 't3.micro,t2.micro'}
    """
    if not isinstance(command_line, str):
        return {}

    command_line = command_line.strip()
    if not command_line:
        return {}

    try:
        # if a value contains a comma separated list, remove any trailing commas and remove whitespace between values
        stripped_args = [
            arg.strip()
            for arg in command_line.split(",")
            if arg.strip() not in (",", "")
        ]
        command_line = ",".join(stripped_args)

        args = shlex.split(command_line)
        parsed_params = {}

        i = 0
        while i < len(args):
            token = args[i]
            if token.startswith("--"):
                # remove the leading -- to extract the key name
                key = token[2:]
                value = None
                if "=" in key:
                    # handles the case where the key and value are separated by an equals sign.
                    key, value = key.split("=", 1)
                elif i + 1 < len(args) and not args[i + 1].startswith("--"):
                    # handles the case where the key and value are separated by a space
                    value = args[i + 1]
                    i += 1  # Skip next token since it's a value
                key = key.strip()
                if len(key) > 0 and value not in (None, ""):
                    parsed_params[key] = (
                        value.strip() if isinstance(value, str) else str(value).strip()
                    )
            i += 1
    except Exception as e:
        logger.error(f"Error parsing command line: {e}")
    return parsed_params


def get_values_for_key_from_dict_of_parameters(key_name: str, dict_of_parameters: dict):
    """
    Given
    1. dict_of_parameters - a dictionary of parameters and associated values e.g.
       {'state': 'pending,stopped', 'type': 't3.micro,t2.micro'}
    2. key_name - the key name e.g. 'state'
    Return the list of values associated with the key e.g. ['pending', 'stopped'] if present or else []
    """
    list_of_values = []
    if (
        key_name
        and dict_of_parameters
        and isinstance(key_name, str)
        and isinstance(dict_of_parameters, dict)
    ):
        values = dict_of_parameters.get(key_name, None)
        if values and isinstance(values, str):
            list_of_values = [
                value.strip() for value in values.split(",") if value not in (",", "")
            ]
    return list_of_values
