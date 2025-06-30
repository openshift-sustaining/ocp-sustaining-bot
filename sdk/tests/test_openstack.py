import unittest.mock as mock
from unittest.mock import Mock, PropertyMock

import pytest

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


@pytest.mark.skip(reason="Refactoring: will update in follow-up PR")
@mock.patch("openstack.connection.Connection")
def test_create_vm(mock_openstack):
    """Test successful creation of a VM."""
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

    mock_compute.create_server.return_value = server
    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    result = openstack_helper.create_vm(
        ["server", "image_rhel-10.iso", "rhel-10", "private"]
    )

    assert result["count"] == 1

    instances = result["instances"]
    assert len(instances) == 1

    assert instances[0].get("name") == "server"

    mock_openstack.assert_called_once()
    mock_compute.create_server.assert_called_once()


@pytest.mark.skip(reason="Refactoring: will update in follow-up PR")
@mock.patch("openstack.connection.Connection")
def test_create_vm_raise_exception(mock_openstack):
    """Test creation of a VM but raise an exception."""
    mock_compute = mock.MagicMock()
    mock_compute.create_server.side_effect = Exception()
    mock_openstack.return_value.compute = mock_compute

    openstack_helper = OpenStackHelper()
    with pytest.raises(Exception) as e:
        openstack_helper.create_vm(
            ["server", "image_rhel-10.iso", "rhel-10", "private"]
        )

    assert isinstance(e.value, Exception)

    mock_openstack.assert_called_once()
    mock_compute.create_server.assert_called_once()


@pytest.mark.skip(reason="Refactoring: will update in follow-up PR")
def test_create_vm_with_less_args():
    """Test creation of a VM with less args."""
    openstack_helper = OpenStackHelper()
    with pytest.raises(ValueError) as e:
        openstack_helper.create_vm(["server"])

    assert isinstance(e.value, ValueError)
    assert (
        e.value.args[0]
        == "Invalid parameters: Usage: `create-openstack-vm <name> <image> <flavor> <network>`"
    )
