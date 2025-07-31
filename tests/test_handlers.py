import unittest.mock as mock
from unittest.mock import MagicMock

from slack_handlers.handlers import handle_aws_modify_vm, handle_openstack_modify_vm


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


# Tests for OpenStack VM lifecycle management handlers


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_stop_success(mock_openstack_helper):
    """Test successful stop operation via handler."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.stop_server.return_value = {
        "success": True,
        "server_id": "test-server-id",
        "server_name": "test-server",
        "previous_status": "ACTIVE",
        "current_status": "stopping",
    }

    params_dict = {"vm-id": "test-server-id", "stop": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_helper_instance.stop_server.assert_called_once_with("test-server-id")
    assert mock_say.call_count == 2
    # Check progress message
    progress_call = mock_say.call_args_list[0][0][0]
    assert ":hourglass_flowing_sand:" in progress_call
    assert "Attempting to stop server" in progress_call
    # Check success message
    result_call = mock_say.call_args_list[1][0][0]
    assert ":white_check_mark:" in result_call
    assert "Successfully initiated stop" in result_call
    assert "test-server" in result_call


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_start_success(mock_openstack_helper):
    """Test successful start operation via handler."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.start_server.return_value = {
        "success": True,
        "server_id": "test-server-id",
        "server_name": "test-server",
        "previous_status": "SHUTOFF",
        "current_status": "starting",
    }

    params_dict = {"vm-id": "test-server-id", "start": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_helper_instance.start_server.assert_called_once_with("test-server-id")
    assert mock_say.call_count == 2
    # Check progress message
    progress_call = mock_say.call_args_list[0][0][0]
    assert ":hourglass_flowing_sand:" in progress_call
    assert "Attempting to start server" in progress_call
    # Check success message
    result_call = mock_say.call_args_list[1][0][0]
    assert ":white_check_mark:" in result_call
    assert "Successfully initiated start" in result_call
    assert "test-server" in result_call


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_delete_success(mock_openstack_helper):
    """Test successful delete operation via handler."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.delete_server.return_value = {
        "success": True,
        "server_id": "test-server-id",
        "server_name": "test-server",
        "previous_status": "ACTIVE",
        "current_status": "deleting",
    }

    params_dict = {"vm-id": "test-server-id", "delete": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_helper_instance.delete_server.assert_called_once_with("test-server-id")
    assert mock_say.call_count == 2
    # Check warning/progress message
    warning_call = mock_say.call_args_list[0][0][0]
    assert ":warning:" in warning_call
    assert "Deletion Warning" in warning_call
    assert "Proceeding with deletion" in warning_call
    # Check success message
    result_call = mock_say.call_args_list[1][0][0]
    assert ":white_check_mark:" in result_call
    assert "Successfully initiated deletion" in result_call
    assert "test-server" in result_call


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_stop_failure(mock_openstack_helper):
    """Test failed stop operation via handler."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.stop_server.return_value = {
        "success": False,
        "error": "Server is already stopped (status: SHUTOFF)",
    }

    params_dict = {"vm-id": "test-server-id", "stop": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_helper_instance.stop_server.assert_called_once_with("test-server-id")
    assert mock_say.call_count == 2
    # Check progress message
    progress_call = mock_say.call_args_list[0][0][0]
    assert ":hourglass_flowing_sand:" in progress_call
    assert "Attempting to stop server" in progress_call
    # Check error message
    error_call = mock_say.call_args_list[1][0][0]
    assert ":x:" in error_call
    assert "Failed to stop server" in error_call
    assert "already stopped" in error_call


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_start_failure(mock_openstack_helper):
    """Test failed start operation via handler."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.start_server.return_value = {
        "success": False,
        "error": "Server is already running (status: ACTIVE)",
    }

    params_dict = {"vm-id": "test-server-id", "start": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_helper_instance.start_server.assert_called_once_with("test-server-id")
    assert mock_say.call_count == 2
    # Check progress message
    progress_call = mock_say.call_args_list[0][0][0]
    assert ":hourglass_flowing_sand:" in progress_call
    assert "Attempting to start server" in progress_call
    # Check error message
    error_call = mock_say.call_args_list[1][0][0]
    assert ":x:" in error_call
    assert "Failed to start server" in error_call
    assert "already running" in error_call


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_delete_failure(mock_openstack_helper):
    """Test failed delete operation via handler."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.delete_server.return_value = {
        "success": False,
        "error": "Server with ID 'test-server-id' not found",
    }

    params_dict = {"vm-id": "test-server-id", "delete": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_helper_instance.delete_server.assert_called_once_with("test-server-id")
    assert mock_say.call_count == 2
    # Check warning/progress message
    warning_call = mock_say.call_args_list[0][0][0]
    assert ":warning:" in warning_call
    assert "Deletion Warning" in warning_call
    # Check error message
    error_call = mock_say.call_args_list[1][0][0]
    assert ":x:" in error_call
    assert "Failed to delete server" in error_call
    assert "not found" in error_call


def test_handle_openstack_modify_vm_missing_vm_id():
    """Test handler with missing vm-id parameter."""
    mock_say = mock.MagicMock()

    params_dict = {"stop": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_say.assert_called_once()
    call_args = mock_say.call_args[0][0]
    assert ":warning:" in call_args
    assert "Missing required parameter" in call_args
    assert "--vm-id" in call_args


def test_handle_openstack_modify_vm_no_action():
    """Test handler with no action specified."""
    mock_say = mock.MagicMock()

    params_dict = {"vm-id": "test-server-id"}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_say.assert_called_once()
    call_args = mock_say.call_args[0][0]
    assert ":warning:" in call_args
    assert "You must specify one action" in call_args
    assert "--stop" in call_args and "--start" in call_args and "--delete" in call_args


def test_handle_openstack_modify_vm_multiple_actions():
    """Test handler with multiple actions specified."""
    mock_say = mock.MagicMock()

    params_dict = {"vm-id": "test-server-id", "stop": True, "start": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_say.assert_called_once()
    call_args = mock_say.call_args[0][0]
    assert ":warning:" in call_args
    assert "Please specify only one action at a time" in call_args
    assert "--stop" in call_args and "--start" in call_args and "--delete" in call_args


def test_handle_openstack_modify_vm_all_three_actions():
    """Test handler with all three actions specified."""
    mock_say = mock.MagicMock()

    params_dict = {
        "vm-id": "test-server-id",
        "stop": True,
        "start": True,
        "delete": True,
    }

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    mock_say.assert_called_once()
    call_args = mock_say.call_args[0][0]
    assert ":warning:" in call_args
    assert "Please specify only one action at a time" in call_args
    assert "--stop" in call_args and "--start" in call_args and "--delete" in call_args


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_exception_handling(mock_openstack_helper):
    """Test handler with unexpected exception."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    # Simulate an exception during the operation
    mock_helper_instance.stop_server.side_effect = Exception("Unexpected error")

    params_dict = {"vm-id": "test-server-id", "stop": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    assert mock_say.call_count == 2
    # Check progress message
    progress_call = mock_say.call_args_list[0][0][0]
    assert ":hourglass_flowing_sand:" in progress_call
    assert "Attempting to stop server" in progress_call
    # Check error message
    error_call = mock_say.call_args_list[1][0][0]
    assert ":x:" in error_call
    assert "An internal error occurred" in error_call


@mock.patch("slack_handlers.handlers.OpenStackHelper")
def test_handle_openstack_modify_vm_with_detailed_response(mock_openstack_helper):
    """Test handler response formatting with detailed server information."""
    mock_say = mock.MagicMock()
    mock_helper_instance = mock.MagicMock()
    mock_openstack_helper.return_value = mock_helper_instance

    mock_helper_instance.stop_server.return_value = {
        "success": True,
        "server_id": "abc123-def456-ghi789",
        "server_name": "production-web-server-01",
        "previous_status": "ACTIVE",
        "current_status": "stopping",
    }

    params_dict = {"vm-id": "abc123-def456-ghi789", "stop": True}

    handle_openstack_modify_vm(mock_say, "test_user", params_dict)

    assert mock_say.call_count == 2
    # Check progress message
    progress_call = mock_say.call_args_list[0][0][0]
    assert ":hourglass_flowing_sand:" in progress_call
    assert "abc123-def456-ghi789" in progress_call
    # Check success message with detailed information
    result_call = mock_say.call_args_list[1][0][0]
    assert ":white_check_mark:" in result_call
    assert "production-web-server-01" in result_call
    assert "abc123-def456-ghi789" in result_call
    assert "ACTIVE" in result_call
    assert "stopping" in result_call
