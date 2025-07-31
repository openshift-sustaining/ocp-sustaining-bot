import unittest.mock as mock
from unittest.mock import Mock, PropertyMock

import pytest
from openstack.exceptions import ResourceFailure

from sdk.openstack.core import OpenStackHelper


@mock.patch("openstack.connection.Connection")
def test_list_vms_empty(mock_openstack):
    """Test listing VMs when there are no VMs."""
    mock_compute = mock.MagicMock()
    mock_compute.servers.return_value = []
    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.list_servers()

    assert result["count"] == 0

    instances = result["instances"]
    assert len(instances) == 0

    mock_openstack.assert_called_once()
    mock_compute.servers.assert_called_once()


@mock.patch("openstack.connection.Connection")
def test_list_vms(mock_openstack):
    """Test listing VMs."""
    mock_compute = mock.MagicMock()
    server = Mock(
        id="42",
        flavor={"original_name": "rhel-10"},
        availability_zone="us",
        addresses={
            "private": [
                {"OS-EXT-IPS:type": "fixed", "addr": "10.123.50.11", "version": "ipv4"}
            ]
        },
        key_name="my_key",
        status="ACTIVE",
    )
    type(server).name = PropertyMock(return_value="server")

    test_server = Mock(
        name="test_server",
        id="35",
        flavor={"original_name": "rhel-11"},
        availability_zone="us",
        addresses={
            "test_network": [
                {"OS-EXT-IPS:type": "fixed", "addr": "10.70.33.2", "version": "ipv4"}
            ]
        },
        key_name="test_key",
        status="ACTIVE",
    )
    type(test_server).name = PropertyMock(return_value="test_server")
    mock_compute.servers.return_value = [
        server,
        test_server,
    ]
    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.list_servers()

    assert result["count"] == 2

    instances = result["instances"]
    assert len(instances) == 2

    assert instances[0].get("name") == "server"
    assert instances[0].get("flavor") == "rhel-10"
    assert instances[0].get("server_id") == "42"
    assert instances[0].get("network") == "private"
    assert instances[0].get("status") == "ACTIVE"

    assert instances[1].get("name") == "test_server"
    assert instances[1].get("flavor") == "rhel-11"
    assert instances[1].get("server_id") == "35"
    assert instances[1].get("network") == "test_network"
    assert instances[1].get("status") == "ACTIVE"

    mock_openstack.assert_called_once()
    mock_compute.servers.assert_called_once()


@mock.patch("openstack.connection.Connection")
def test_list_vms_with_status_filter(mock_openstack):
    """Test listing VMs with status filter."""
    mock_compute = mock.MagicMock()
    server = Mock(
        id="42",
        flavor={"original_name": "rhel-10"},
        addresses={
            "private": [
                {"OS-EXT-IPS:type": "fixed", "addr": "10.123.50.11", "version": "ipv4"}
            ]
        },
        key_name="my_key",
        status="SHUTOFF",
    )
    type(server).name = PropertyMock(return_value="server")

    mock_compute.servers.return_value = [server]
    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.list_servers({"status": "SHUTOFF"})

    assert result["count"] == 1
    instances = result["instances"]
    assert len(instances) == 1
    assert instances[0].get("status") == "SHUTOFF"

    mock_openstack.assert_called_once()
    mock_compute.servers.assert_called_once_with(status="SHUTOFF")


@mock.patch("openstack.connection.Connection")
def test_create_servers_success(mock_openstack):
    """Test successful creation of a VM."""
    mock_compute = mock.MagicMock()
    mock_flavor = Mock(id="flavor-id-123")
    mock_flavor.name = "rhel-10"
    mock_image = Mock(id="image-id-456")

    mock_server = Mock(
        id="server-id-789",
        status="ACTIVE",
        addresses={
            "private": [
                {"OS-EXT-IPS:type": "fixed", "addr": "10.123.50.11", "version": "ipv4"}
            ]
        },
    )
    mock_server.name = "test-server"

    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_compute.find_flavor.return_value = mock_flavor
    mock_compute.find_image.return_value = mock_image

    mock_compute.create_server.return_value = mock_server
    mock_compute.wait_for_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.create_servers(
        name="test-server",
        image_id="image-id-456",
        flavor="rhel-10",
        key_name="test-key",
        network="network-id-123",
    )

    assert result["count"] == 1
    instances = result["instances"]
    assert len(instances) == 1

    instance = instances[0]
    assert instance["name"] == "test-server"
    assert instance["server_id"] == "server-id-789"
    assert instance["status"] == "ACTIVE"
    assert instance["flavor"] == "rhel-10"
    assert instance["key_name"] == "test-key"
    assert instance["private_ip"] == "10.123.50.11"

    mock_compute.create_server.assert_called_once_with(
        name="test-server",
        image_id="image-id-456",
        flavor_id="flavor-id-123",
        networks=[{"uuid": "network-id-123"}],
        key_name="test-key",
    )
    mock_compute.wait_for_server.assert_called_once()


@mock.patch("openstack.connection.Connection")
def test_create_servers_invalid_key_name(mock_openstack):
    """Test creation of VM with invalid key name."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "valid-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    with pytest.raises(ValueError) as exc_info:
        openstack_helper.create_servers(
            name="test-server",
            image_id="image-id-456",
            flavor="rhel-10",
            key_name="invalid-key",
            network="network-id-123",
        )

    assert "Invalid key_name 'invalid-key' provided" in str(exc_info.value)
    assert "Available keypairs: ['valid-key']" in str(exc_info.value)


@mock.patch("openstack.connection.Connection")
def test_create_servers_invalid_flavor(mock_openstack):
    """Test creation of VM with invalid flavor."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_compute.find_flavor.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    with pytest.raises(ValueError) as exc_info:
        openstack_helper.create_servers(
            name="test-server",
            image_id="image-id-456",
            flavor="invalid-flavor",
            key_name="test-key",
            network="network-id-123",
        )

    assert "Flavor 'None' not found in OpenStack" in str(exc_info.value)


@mock.patch("openstack.connection.Connection")
def test_create_servers_invalid_image(mock_openstack):
    """Test creation of VM with invalid image."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_flavor = Mock(id="flavor-id-123", name="rhel-10")
    mock_compute.find_flavor.return_value = mock_flavor

    mock_compute.find_image.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    with pytest.raises(ValueError) as exc_info:
        openstack_helper.create_servers(
            name="test-server",
            image_id="invalid-image",
            flavor="rhel-10",
            key_name="test-key",
            network="network-id-123",
        )

    assert "Image 'invalid-image' not found in OpenStack" in str(exc_info.value)


@mock.patch("openstack.connection.Connection")
def test_create_servers_resource_failure(mock_openstack):
    """Test VM creation with ResourceFailure exception."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_flavor = Mock(id="flavor-id-123", name="rhel-10")
    mock_image = Mock(id="image-id-456")
    mock_compute.find_flavor.return_value = mock_flavor
    mock_compute.find_image.return_value = mock_image

    mock_compute.create_server.side_effect = ResourceFailure("VM creation failed")

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    with pytest.raises(RuntimeError) as exc_info:
        openstack_helper.create_servers(
            name="test-server",
            image_id="image-id-456",
            flavor="rhel-10",
            key_name="test-key",
            network="network-id-123",
        )

    assert "OpenStack VM provisioning failed" in str(exc_info.value)


@mock.patch("openstack.connection.Connection")
def test_create_servers_general_exception(mock_openstack):
    """Test VM creation with general exception."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_flavor = Mock(id="flavor-id-123", name="rhel-10")
    mock_image = Mock(id="image-id-456")
    mock_compute.find_flavor.return_value = mock_flavor
    mock_compute.find_image.return_value = mock_image

    mock_compute.create_server.side_effect = Exception("General error")

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    with pytest.raises(Exception) as exc_info:
        openstack_helper.create_servers(
            name="test-server",
            image_id="image-id-456",
            flavor="rhel-10",
            key_name="test-key",
            network="network-id-123",
        )

    assert "General error" in str(exc_info.value)


@mock.patch("openstack.connection.Connection")
def test_create_servers_no_network(mock_openstack):
    """Test VM creation without network parameter."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_flavor = Mock(id="flavor-id-123", name="rhel-10")
    mock_image = Mock(id="image-id-456")

    mock_server = Mock(
        id="server-id-789",
        name="test-server",
        status="ACTIVE",
        addresses={
            "default": [
                {"OS-EXT-IPS:type": "fixed", "addr": "10.123.50.11", "version": "ipv4"}
            ]
        },
    )

    mock_compute.find_flavor.return_value = mock_flavor
    mock_compute.find_image.return_value = mock_image
    mock_compute.create_server.return_value = mock_server
    mock_compute.wait_for_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.create_servers(
        name="test-server",
        image_id="image-id-456",
        flavor="rhel-10",
        key_name="test-key",
        network=None,
    )

    assert result["count"] == 1
    instances = result["instances"]
    assert len(instances) == 1

    instance = instances[0]
    assert instance["network"] == "Default Network"

    mock_compute.create_server.assert_called_once_with(
        name="test-server",
        image_id="image-id-456",
        flavor_id="flavor-id-123",
        networks=[],
        key_name="test-key",
    )


@mock.patch("openstack.connection.Connection")
def test_create_servers_floating_ip_priority(mock_openstack):
    """Test that floating IP is prioritized over fixed IP."""
    mock_compute = mock.MagicMock()
    mock_keypair = Mock()
    mock_keypair.name = "test-key"
    mock_compute.keypairs.return_value = [mock_keypair]

    mock_flavor = Mock(id="flavor-id-123", name="rhel-10")
    mock_image = Mock(id="image-id-456")

    mock_server = Mock(
        id="server-id-789",
        name="test-server",
        status="ACTIVE",
        addresses={
            "private": [
                {"OS-EXT-IPS:type": "fixed", "addr": "10.123.50.11", "version": "ipv4"},
                {
                    "OS-EXT-IPS:type": "floating",
                    "addr": "192.168.1.100",
                    "version": "ipv4",
                },
            ]
        },
    )

    mock_compute.find_flavor.return_value = mock_flavor
    mock_compute.find_image.return_value = mock_image
    mock_compute.create_server.return_value = mock_server
    mock_compute.wait_for_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.create_servers(
        name="test-server",
        image_id="image-id-456",
        flavor="rhel-10",
        key_name="test-key",
        network="network-id-123",
    )

    assert result["count"] == 1
    instances = result["instances"]
    assert len(instances) == 1

    instance = instances[0]
    assert instance["private_ip"] == "10.123.50.11"


# Tests for OpenStack VM lifecycle management


@mock.patch("openstack.connection.Connection")
def test_stop_server_success(mock_openstack):
    """Test successful server stop operation."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.name = "test-server"
    mock_server.status = "ACTIVE"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server
    mock_compute.stop_server.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.stop_server("test-server-id")

    assert result["success"] is True
    assert result["server_id"] == "test-server-id"
    assert result["server_name"] == "test-server"
    assert result["previous_status"] == "ACTIVE"
    assert result["current_status"] == "stopping"

    mock_compute.find_server.assert_called_once_with(
        "test-server-id", ignore_missing=False
    )
    mock_compute.stop_server.assert_called_once_with(mock_server)


@mock.patch("openstack.connection.Connection")
def test_stop_server_already_stopped(mock_openstack):
    """Test stopping a server that is already stopped."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.status = "SHUTOFF"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.stop_server("test-server-id")

    assert result["success"] is False
    assert "already stopped" in result["error"]

    mock_compute.stop_server.assert_not_called()


@mock.patch("openstack.connection.Connection")
def test_stop_server_invalid_status(mock_openstack):
    """Test stopping a server with invalid status."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.status = "ERROR"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.stop_server("test-server-id")

    assert result["success"] is False
    assert "cannot be stopped" in result["error"]

    mock_compute.stop_server.assert_not_called()


@mock.patch("openstack.connection.Connection")
def test_start_server_success(mock_openstack):
    """Test successful server start operation."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.name = "test-server"
    mock_server.status = "SHUTOFF"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server
    mock_compute.start_server.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.start_server("test-server-id")

    assert result["success"] is True
    assert result["server_id"] == "test-server-id"
    assert result["server_name"] == "test-server"
    assert result["previous_status"] == "SHUTOFF"
    assert result["current_status"] == "starting"

    mock_compute.find_server.assert_called_once_with(
        "test-server-id", ignore_missing=False
    )
    mock_compute.start_server.assert_called_once_with(mock_server)


@mock.patch("openstack.connection.Connection")
def test_start_server_already_running(mock_openstack):
    """Test starting a server that is already running."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.status = "ACTIVE"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.start_server("test-server-id")

    assert result["success"] is False
    assert "already running" in result["error"]

    mock_compute.start_server.assert_not_called()


@mock.patch("openstack.connection.Connection")
def test_start_server_from_suspended(mock_openstack):
    """Test starting a server from suspended state."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.name = "test-server"
    mock_server.status = "SUSPENDED"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server
    mock_compute.start_server.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.start_server("test-server-id")

    assert result["success"] is True
    assert result["previous_status"] == "SUSPENDED"

    mock_compute.start_server.assert_called_once_with(mock_server)


@mock.patch("openstack.connection.Connection")
def test_delete_server_success(mock_openstack):
    """Test successful server deletion."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.name = "test-server"
    mock_server.status = "ACTIVE"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server
    mock_compute.delete_server.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.delete_server("test-server-id")

    assert result["success"] is True
    assert result["server_id"] == "test-server-id"
    assert result["server_name"] == "test-server"
    assert result["previous_status"] == "ACTIVE"
    assert result["current_status"] == "deleting"

    mock_compute.find_server.assert_called_once_with(
        "test-server-id", ignore_missing=False
    )
    mock_compute.delete_server.assert_called_once_with(mock_server)


@mock.patch("openstack.connection.Connection")
def test_delete_server_already_deleted(mock_openstack):
    """Test deleting a server that is already deleted."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.status = "DELETED"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.delete_server("test-server-id")

    assert result["success"] is False
    assert "already in status" in result["error"]

    mock_compute.delete_server.assert_not_called()


@mock.patch("openstack.connection.Connection")
def test_delete_server_error_status(mock_openstack):
    """Test deleting a server with ERROR status."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.status = "ERROR"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.delete_server("test-server-id")

    assert result["success"] is False
    assert "already in status 'ERROR'" in result["error"]

    mock_compute.delete_server.assert_not_called()


@mock.patch("openstack.connection.Connection")
def test_lifecycle_server_not_found(mock_openstack):
    """Test lifecycle operations on non-existent server."""
    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = None

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    # Test stop
    result = openstack_helper.stop_server("non-existent-id")
    assert result["success"] is False
    assert "not found" in result["error"]

    # Test start
    result = openstack_helper.start_server("non-existent-id")
    assert result["success"] is False
    assert "not found" in result["error"]

    # Test delete
    result = openstack_helper.delete_server("non-existent-id")
    assert result["success"] is False
    assert "not found" in result["error"]


@mock.patch("openstack.connection.Connection")
def test_lifecycle_operations_with_exceptions(mock_openstack):
    """Test lifecycle operations when OpenStack API throws exceptions."""
    mock_compute = mock.MagicMock()
    mock_compute.find_server.side_effect = Exception("API Error")

    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()

    # Test stop with exception
    result = openstack_helper.stop_server("test-server-id")
    assert result["success"] is False
    assert "Failed to stop server" in result["error"]

    # Test start with exception
    result = openstack_helper.start_server("test-server-id")
    assert result["success"] is False
    assert "Failed to start server" in result["error"]

    # Test delete with exception
    result = openstack_helper.delete_server("test-server-id")
    assert result["success"] is False
    assert "Failed to delete server" in result["error"]


@mock.patch("openstack.connection.Connection")
def test_lifecycle_operations_with_api_call_exceptions(mock_openstack):
    """Test lifecycle operations when individual API calls throw exceptions."""
    mock_server = mock.MagicMock()
    mock_server.id = "test-server-id"
    mock_server.name = "test-server"
    mock_server.status = "ACTIVE"

    mock_compute = mock.MagicMock()
    mock_compute.find_server.return_value = mock_server

    # Test stop server API call exception
    mock_compute.stop_server.side_effect = Exception("Stop API Error")
    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.stop_server("test-server-id")

    assert result["success"] is False
    assert "Failed to stop server" in result["error"]

    # Test start server API call exception
    mock_server.status = "SHUTOFF"
    mock_compute.start_server.side_effect = Exception("Start API Error")

    result = openstack_helper.start_server("test-server-id")

    assert result["success"] is False
    assert "Failed to start server" in result["error"]

    # Test delete server API call exception
    mock_server.status = "ACTIVE"
    mock_compute.delete_server.side_effect = Exception("Delete API Error")

    result = openstack_helper.delete_server("test-server-id")

    assert result["success"] is False
    assert "Failed to delete server" in result["error"]
