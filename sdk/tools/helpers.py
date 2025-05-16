def get_dict_of_command_parameters(command_line: str):
    """
    Given a command line (e.g., list-aws-vms --type=t3.micro,t2.micro --state=pending,stopped),
    remove the main command parameter, parse the remaining parameters,
    and return a dictionary with parameter names as keys and their associated values.
    """
    command_params_dict = {}

    if command_line and isinstance(command_line, str):
        sub_params = command_line.split(" ")

        # Remove any empty strings caused by multiple spaces
        valid_cmd_strings = [
            sub_param.strip() for sub_param in sub_params if sub_param.strip()
        ]

        # Skip the first value, which is the main command (e.g., 'list-aws-vms')
        if len(valid_cmd_strings) > 1:
            valid_cmd_strings = valid_cmd_strings[1:]

            for param in valid_cmd_strings:
                # Split at the first '=' to handle each parameter correctly
                if "=" in param:
                    key, value = param.split("=", 1)
                    key = key.lstrip("--")  # Remove leading '--'

                    # If the value contains commas, split it into a list (for multiple values)
                    command_params_dict[key] = (
                        value.split(",") if "," in value else value
                    )

                else:
                    # Handle the case where '=' is missing (invalid format)
                    logger.warning(
                        f"Skipping invalid parameter (missing '=' in: {param})"
                    )

    return command_params_dict


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
            list_of_values = [value.strip() for value in values.split(",")]
    return list_of_values
