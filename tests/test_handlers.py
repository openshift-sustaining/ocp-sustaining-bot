import unittest.mock as mock
from unittest.mock import MagicMock

from slack_handlers.handlers import handle_aws_modify_vm


@mock.patch("slack_handlers.handlers.EC2Helper")
def test_handle_aws_modify_vm_stop_success(mock_ec2_helper):
    """Test successful stop command."""
    mock_ec2 = MagicMock()
    mock_ec2_helper.return_value = mock_ec2

    mock_ec2.stop_instance.return_value = {
        "success": True,
        "instance_id": "i-1234567890",
        "previous_state": "running",
        "current_state": "stopping",
    }

    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"stop": True, "vm-id": "i-1234567890"},
    )

    mock_ec2_helper.assert_called_once_with(region="us-east-1")

    mock_ec2.stop_instance.assert_called_once_with("i-1234567890")

    calls = mock_say.call_args_list
    assert len(calls) == 2
    assert "Attempting to stop" in calls[0][0][0]
    assert "Successfully initiated stop" in calls[1][0][0]
    assert "i-1234567890" in calls[1][0][0]


@mock.patch("slack_handlers.handlers.EC2Helper")
def test_handle_aws_modify_vm_delete_success(mock_ec2_helper):
    """Test successful delete command."""
    mock_ec2 = MagicMock()
    mock_ec2_helper.return_value = mock_ec2

    mock_ec2.terminate_instance.return_value = {
        "success": True,
        "instance_id": "i-1234567890",
        "instance_name": "test-instance",
        "previous_state": "running",
        "current_state": "shutting-down",
    }

    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"delete": True, "vm-id": "i-1234567890"},
    )

    mock_ec2_helper.assert_called_once_with(region="us-east-1")

    mock_ec2.terminate_instance.assert_called_once_with("i-1234567890")

    calls = mock_say.call_args_list
    assert len(calls) == 2
    assert "Termination Warning" in calls[0][0][0]
    assert "Successfully initiated termination" in calls[1][0][0]
    assert "test-instance" in calls[1][0][0]


@mock.patch("slack_handlers.handlers.EC2Helper")
def test_handle_aws_modify_vm_missing_vm_id(mock_ec2_helper):
    """Test handle_aws_modify_vm with missing vm-id parameter."""
    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"stop": True},
    )

    mock_ec2_helper.assert_not_called()

    mock_say.assert_called_once()
    assert "Missing required parameter" in mock_say.call_args[0][0]
    assert "--vm-id" in mock_say.call_args[0][0]


@mock.patch("slack_handlers.handlers.EC2Helper")
def test_handle_aws_modify_vm_missing_action(mock_ec2_helper):
    """Test handle_aws_modify_vm with missing action."""
    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"vm-id": "i-1234567890"},
    )

    mock_ec2_helper.assert_not_called()

    mock_say.assert_called_once()
    assert "must specify either" in mock_say.call_args[0][0]
    assert "--stop" in mock_say.call_args[0][0]
    assert "--delete" in mock_say.call_args[0][0]


@mock.patch("slack_handlers.handlers.EC2Helper")
def test_handle_aws_modify_vm_both_actions(mock_ec2_helper):
    """Test handle_aws_modify_vm with both stop and delete actions specified."""
    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"stop": True, "delete": True, "vm-id": "i-1234567890"},
    )

    mock_ec2_helper.assert_not_called()

    mock_say.assert_called_once()
    assert "only one action" in mock_say.call_args[0][0]
    assert "not both" in mock_say.call_args[0][0]


@mock.patch("slack_handlers.handlers.EC2Helper")
def test_handle_aws_modify_vm_stop_failure(mock_ec2_helper):
    """Test handle_aws_modify_vm when stop operation fails."""
    mock_ec2 = MagicMock()
    mock_ec2_helper.return_value = mock_ec2

    mock_ec2.stop_instance.return_value = {
        "success": False,
        "error": "Instance i-1234567890 is already stopped",
    }

    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"stop": True, "vm-id": "i-1234567890"},
    )

    calls = mock_say.call_args_list
    assert len(calls) == 2
    assert "Failed to stop instance" in calls[1][0][0]


@mock.patch("slack_handlers.handlers.EC2Helper")
@mock.patch("slack_handlers.handlers.logger")
def test_handle_aws_modify_vm_exception(mock_logger, mock_ec2_helper):
    """Test handle_aws_modify_vm when an exception occurs."""
    mock_ec2_helper.side_effect = Exception("Connection error")

    mock_say = MagicMock()

    handle_aws_modify_vm(
        say=mock_say,
        region="us-east-1",
        user="test-user",
        params_dict={"stop": True, "vm-id": "i-1234567890"},
    )

    mock_logger.error.assert_called()

    mock_say.assert_called_once()
    assert "internal error occurred" in mock_say.call_args[0][0]
    assert "contact the administrator" in mock_say.call_args[0][0]
