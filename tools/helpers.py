def get_dict_of_command_parameters(command_line: str, texts_to_remove=None):
    """
    Given
    1. command_line - the command line e.g. list-aws-vms --type=t3.micro,t2.micro --state=pending,stopped
    2. texts_to_remove - the list of strings to remove e.g. ['list-aws-vms']

    3. remove the command parameter specified in the texts_to_remove list e.g. ['list-aws-vms']
    4. parse the remaining text and return a dictionary of parameters and a list of associated values if present else {}
       For example, {'--state': 'pending,stopped', '--type': 't3.micro,t2.micro'}
    """
    command_params_dict = {}
    if command_line and isinstance(command_line, str):
        if texts_to_remove and isinstance(texts_to_remove, list):
            for text_to_remove in texts_to_remove:
                command_line = command_line.replace(text_to_remove, "")
        sub_params = command_line.split(" ")
        # remove any empty strings which will be there if there were > 1 spaces between parameters
        valid_cmd_strings = [sub_param for sub_param in sub_params if sub_param != ""]
        command_params_dict = dict(
            (k, v) for k, v in (pair.split("=") for pair in valid_cmd_strings)
        )
    return command_params_dict


def get_values_for_key_from_dict_of_parameters(key_name: str, dict_of_parameters: dict):
    """
    Given
    1. dict_of_parameters - a dictionary of parameters and associated values e.g.
       {'--state': 'pending,stopped', '--type': 't3.micro,t2.micro'}
    2. key_name - the key name e.g. '--state'
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
