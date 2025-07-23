from sdk.tools.helpers import (
    get_named_and_positional_params,
    get_list_of_values_for_key_in_dict_of_parameters,
)


def test_get_named_and_positional_params_when_no_params():
    named_params, positional_params = get_named_and_positional_params("aws vm list")
    assert len(named_params) == 0
    assert len(positional_params) == 0


def test_get_named_and_positional_params_when_no_key_value_params():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list something else"
    )
    assert len(named_params) == 0
    assert "something" == positional_params[0]
    assert "else" == positional_params[1]


def test_get_named_and_positional_params_when_mixture_param_types():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list paramA paramB --type=t3.micro,t2.micro --state=pending,stopped spaces spaces2"
    )
    assert "t3.micro,t2.micro" == named_params.get("type")
    assert "pending,stopped spaces spaces2" == named_params.get("state")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_named_and_positional_params_when_using_positional_params():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm create linux 1.2.3"
    )
    assert len(named_params) == 0
    assert "linux" == positional_params[0]
    assert "1.2.3" == positional_params[1]


def test_get_named_and_positional_params_when_single_value_params_with_equals_separator():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list --type=t3.micro --state=pending"
    )
    assert "t3.micro" == named_params.get("type")
    assert "pending" == named_params.get("state")
    assert not positional_params


def test_get_named_and_positional_params_when_single_value_params_with_no_equals_separator():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list --type  t3.micro --state  pending"
    )
    assert "t3.micro" == named_params.get("type")
    assert "pending" == named_params.get("state")
    assert len(positional_params) == 0


def test_get_named_and_positional_params_when_no_equals_separator():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list --type  t3.micro, t2.micro, t1.micro --state  pending"
    )
    assert named_params.get("type") == "t3.micro,t2.micro,t1.micro"
    assert named_params.get("state") == "pending"
    assert not positional_params


def test_get_named_and_positional_params_when_good_params_with_no_equals_separator():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list paramA paramB --type t3.micro,t2.micro --state pending,stopped"
    )
    assert "t3.micro,t2.micro" == named_params.get("type")
    assert "pending,stopped" == named_params.get("state")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_named_and_positional_params_when_mixture_good_params():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list paramA paramB --type t3.micro,t2.micro --state=pending,stopped"
    )
    assert "t3.micro,t2.micro" == named_params.get("type")
    assert "pending,stopped" == named_params.get("state")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_named_and_positional_params_when_value_has_spaces():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm list paramA paramB --desc some value with space --state pending"
    )
    assert "some value with space" == named_params.get("desc")
    assert "pending" == named_params.get("state")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_dict_when_command_has_extra_spaces():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm create paramA paramB  --os_name=linux    --instance_type=t2.micro  --key_pair=my-key"
    )
    assert "linux" == named_params.get("os_name")
    assert "t2.micro" == named_params.get("instance_type")
    assert "my-key" == named_params.get("key_pair")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_dict_when_spaces_between_params():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm create   paramA   paramB  --state=pending, stopped , running"
    )
    assert "pending,stopped,running" == named_params.get("state")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_dict_when_trailing_commas_between_params():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm create --state=pending, stopped, "
    )
    assert "pending,stopped" == named_params.get("state")
    named_params, positional_params = get_named_and_positional_params(
        "aws vm create paramA paramB --state=pending,,, stopped,,,, "
    )
    assert "pending,stopped" == named_params.get("state")
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_dict_when_multi_words_in_command_line():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm create paramA paramB --vm-id=i-123456 --multi=these are values --state=pending, stopped"
    )
    assert named_params.get("state") == "pending,stopped"
    assert named_params.get("vm-id") == "i-123456"
    assert named_params.get("multi") == "these are values"
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_dict_with_flag_parameters():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm modify paramA paramB --stop --vm-id=i-123456"
    )
    assert named_params.get("stop") is True
    assert named_params.get("vm-id") == "i-123456"
    assert "paramA" == positional_params[0]
    assert "paramB" == positional_params[1]


def test_get_dict_with_multiple_flag_parameters():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm modify paramA --flag1 --flag2 --value=test"
    )
    assert named_params.get("flag1") is True
    assert named_params.get("flag2") is True
    assert named_params.get("value") == "test"
    assert "paramA" == positional_params[0]


def test_get_dict_with_only_flag_parameters():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm modify --stop --delete"
    )
    assert named_params.get("stop") is True
    assert named_params.get("delete") is True
    assert len(named_params) == 2
    assert len(positional_params) == 0


def test_get_list_of_values_for_key_in_dict_of_parameters_when_absent_key():
    named_params, positional_params = get_named_and_positional_params(
        "aws vm modify --stop --delete"
    )
    result = named_params.get("absent_key")
    assert result is None
    assert len(positional_params) == 0


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
