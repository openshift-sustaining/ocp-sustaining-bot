from sdk.tools.helpers import (
    process_command_parameters,
    get_list_of_values_for_key_in_dict_of_parameters,
)


def test_get_dict_of_command_parameters_when_no_params():
    params_dict, list_params = process_command_parameters("list-aws-vms")
    assert len(params_dict) == 0
    assert len(list_params) == 0


def test_get_dict_of_command_parameters_when_no_key_value_params():
    params_dict, list_params = process_command_parameters("list-aws-vms something else")
    assert len(params_dict) == 0
    assert "something" == list_params[0]
    assert "else" == list_params[1]


def test_get_dict_of_command_parameters_when_mixture_param_types():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms paramA paramB --type=t3.micro,t2.micro --state=pending,stopped spaces spaces2"
    )
    assert "t3.micro,t2.micro" == params_dict.get("type")
    assert "pending,stopped spaces spaces2" == params_dict.get("state")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_of_command_parameters_when_rota_command():
    params_dict, list_params = process_command_parameters("rota add 1.2.3")
    assert len(params_dict) == 0
    assert "add" == list_params[0]
    assert "1.2.3" == list_params[1]


def test_get_dict_of_command_parameters_when_single_value_params_with_equals_separator():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms --type=t3.micro --state=pending"
    )
    assert "t3.micro" == params_dict.get("type")
    assert "pending" == params_dict.get("state")
    assert len(list_params) == 0


def test_get_dict_of_command_parameters_when_single_value_params_with_no_equals_separator():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms --type  t3.micro --state  pending"
    )
    assert "t3.micro" == params_dict.get("type")
    assert "pending" == params_dict.get("state")
    assert len(list_params) == 0


def test_get_dict_of_command_parameters_when_no_equals_separator():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms --type  t3.micro, t2.micro, t1.micro --state  pending"
    )
    assert params_dict.get("type") == "t3.micro,t2.micro,t1.micro"
    assert params_dict.get("state") == "pending"
    assert len(list_params) == 0


def test_get_dict_of_command_parameters_when_good_params_with_no_equals_separator():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms paramA paramB --type t3.micro,t2.micro --state pending,stopped"
    )
    assert "t3.micro,t2.micro" == params_dict.get("type")
    assert "pending,stopped" == params_dict.get("state")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_of_command_parameters_when_mixture_good_params():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms paramA paramB --type t3.micro,t2.micro --state=pending,stopped"
    )
    assert "t3.micro,t2.micro" == params_dict.get("type")
    assert "pending,stopped" == params_dict.get("state")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_of_command_parameters_when_value_has_spaces():
    params_dict, list_params = process_command_parameters(
        "list-aws-vms paramA paramB --desc some value with space --state pending"
    )
    assert "some value with space" == params_dict.get("desc")
    assert "pending" == params_dict.get("state")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_when_command_has_extra_spaces():
    params_dict, list_params = process_command_parameters(
        "create-aws-vm paramA paramB  --os_name=linux    --instance_type=t2.micro  --key_pair=my-key"
    )
    assert "linux" == params_dict.get("os_name")
    assert "t2.micro" == params_dict.get("instance_type")
    assert "my-key" == params_dict.get("key_pair")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_when_spaces_between_params():
    params_dict, list_params = process_command_parameters(
        "create-aws-vm   paramA   paramB  --state=pending, stopped , running"
    )
    assert "pending,stopped,running" == params_dict.get("state")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_when_trailing_commas_between_params():
    params_dict, list_params = process_command_parameters(
        "create-aws-vm --state=pending, stopped, "
    )
    assert "pending,stopped" == params_dict.get("state")
    params_dict, list_params = process_command_parameters(
        "create-aws-vm paramA paramB --state=pending,,, stopped,,,, "
    )
    assert "pending,stopped" == params_dict.get("state")
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_when_multi_words_in_command_line():
    params_dict, list_params = process_command_parameters(
        "command paramA paramB --vm-id=i-123456 --multi=these are values --state=pending, stopped"
    )
    assert params_dict.get("state") == "pending,stopped"
    assert params_dict.get("vm-id") == "i-123456"
    assert params_dict.get("multi") == "these are values"
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_with_flag_parameters():
    params_dict, list_params = process_command_parameters(
        "aws-modify-vm paramA paramB --stop --vm-id=i-123456"
    )
    assert params_dict.get("stop") is True
    assert params_dict.get("vm-id") == "i-123456"
    assert "paramA" == list_params[0]
    assert "paramB" == list_params[1]


def test_get_dict_with_multiple_flag_parameters():
    params_dict, list_params = process_command_parameters(
        "command paramA --flag1 --flag2 --value=test"
    )
    assert params_dict.get("flag1") is True
    assert params_dict.get("flag2") is True
    assert params_dict.get("value") == "test"
    assert "paramA" == list_params[0]


def test_get_dict_with_only_flag_parameters():
    params_dict, list_params = process_command_parameters("command --stop --delete")
    assert params_dict.get("stop") is True
    assert params_dict.get("delete") is True
    assert len(params_dict) == 2
    assert len(list_params) == 0


def test_get_list_of_values_for_key_in_dict_of_parameters_when_absent_key():
    params_dict, list_params = process_command_parameters("command --stop --delete")
    result = params_dict.get("absent_key")
    assert result is None
    assert len(list_params) == 0


def test_get_list_of_values_for_key_in_dict_of_parameters_when_present_in_dict_params():
    param_dict = {"state": "pending,stopped", "type": "t2.micro,t3.micro"}
    result = get_list_of_values_for_key_in_dict_of_parameters("type", param_dict)
    assert result == ["t2.micro", "t3.micro"]


def test_get_list_of_values_for_key_in_dict_of_parameters_when_absent_in_dict_params():
    param_dict = {"state": "pending,stopped", "type": "t2.micro,t3.micro"}
    result = get_list_of_values_for_key_in_dict_of_parameters("missing_key", param_dict)
    assert len(result) == 0


def test_get_list_of_values_for_key_in_dict_of_parameters_when_spaces_in_dict_params():
    param_dict = {"state": "pending, stopped,  running", "type": "t2.micro,t3.micro"}
    result = get_list_of_values_for_key_in_dict_of_parameters("state", param_dict)
    assert result == ["pending", "stopped", "running"]
