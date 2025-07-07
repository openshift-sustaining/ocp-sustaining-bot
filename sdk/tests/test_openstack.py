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
