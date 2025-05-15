from sdk.tools.helpers import get_dict_of_command_parameters


def test_get_dict_of_command_parameters_when_no_params():
    params_dict = get_dict_of_command_parameters("list-aws-vms")
    assert len(params_dict) == 0


def test_get_dict_of_command_parameters_when_no_key_value_params():
    params_dict = get_dict_of_command_parameters("list-aws-vms something else")
    assert len(params_dict) == 0


def test_get_dict_of_command_parameters_when_good_params_with_equals_separator():
    params_dict = get_dict_of_command_parameters(
        "list-aws-vms --type=t3.micro,t2.micro --state=pending,stopped"
    )
    assert "t3.micro,t2.micro" == params_dict.get("type")
    assert "pending,stopped" == params_dict.get("state")


def test_get_dict_of_command_parameters_when_good_params_with_no_equals_separator():
    params_dict = get_dict_of_command_parameters(
        "list-aws-vms --type t3.micro,t2.micro --state pending,stopped"
    )
    assert "t3.micro,t2.micro" == params_dict.get("type")
    assert "pending,stopped" == params_dict.get("state")


def test_get_dict_of_command_parameters_when_mixture_good_params():
    params_dict = get_dict_of_command_parameters(
        "list-aws-vms --type t3.micro,t2.micro --state=pending,stopped"
    )
    assert "t3.micro,t2.micro" == params_dict.get("type")
    assert "pending,stopped" == params_dict.get("state")
