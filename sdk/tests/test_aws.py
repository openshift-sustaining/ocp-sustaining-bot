import unittest.mock as mock
import botocore.exceptions
from unittest.mock import Mock

from sdk.aws.ec2 import EC2Helper


@mock.patch("boto3.Session")
def test_list_instances_empty(mock_boto3_session):
    """Test listing instances when there are no instances."""
    mock_client = mock.MagicMock()
    mock_client.describe_instances.return_value = {"Reservations": []}
    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="eu-west-2")
    result = ec2_helper.list_instances()
    assert result == {"count": 0, "instances": []}

    mock_boto3_session.assert_called_once()
    mock_boto3_session.return_value.client.assert_called_once_with("ec2")
    mock_client.describe_instances.assert_called_once()


@mock.patch("boto3.Session")
def test_list_instances(mock_boto3_session):
    """Test listing EC2 instances."""
    mock_client = mock.MagicMock()
    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-3651695",
                        "InstanceType": "t2.micro",
                        "State": {"Name": "running"},
                    },
                    {
                        "InstanceId": "i-78435671",
                        "InstanceType": "t2.small",
                        "State": {"Name": "stopped"},
                    },
                ]
            }
        ]
    }
    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="ap-southeast-1")
    result = ec2_helper.list_instances()

    assert result["count"] == 2

    instances = result["instances"]
    assert len(instances) == 2
    assert instances[0]["instance_id"] == "i-3651695"
    assert instances[0]["instance_type"] == "t2.micro"
    assert instances[0]["state"] == "running"

    assert instances[1]["instance_id"] == "i-78435671"
    assert instances[1]["instance_type"] == "t2.small"
    assert instances[1]["state"] == "stopped"

    mock_boto3_session.assert_called_once()
    mock_boto3_session.return_value.client.assert_called_once_with("ec2")
    mock_client.describe_instances.assert_called_once()


@mock.patch("boto3.client")
@mock.patch("boto3.Session")
def test_create_instance_success(mock_boto3_session, mock_boto3_client):
    """Test successful creation of an EC2 instance."""
    mock_resource = mock.MagicMock()
    mock_resource.create_instances.return_value = [
        Mock(id="i-3651695", instance_type="t2.micro", state={"Name": "running"}),
    ]
    mock_boto3_session.return_value.resource.return_value = mock_resource

    mock_client = mock.MagicMock()
    mock_client.describe_subnets.return_value = {
        "Subnets": [{"SubnetId": "subnet-on-vpc"}]
    }
    mock_client.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-for-testing"}]}
    mock_client.describe_security_groups.return_value = {
        "SecurityGroups": [{"GroupId": "sg-12345"}]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    mock_boto3_client.return_value.get_caller_identity.return_value = {
        "Arn": "test-arn/redhat"
    }

    region = "ca-central-1"
    ec2_helper = EC2Helper(region=region)
    image_id = "rhel-10"
    instance_type = "t2.nano"
    key_name = "test-key-pair"
    security_group_id = "sg-12345"
    subnet_id = "subnet-on-vpc"

    instance_create = ec2_helper.create_instance(
        image_id=image_id,
        instance_type=instance_type,
        key_name=key_name,
    )

    assert instance_create["count"] == 1
    assert len(instance_create["instances"]) == 1
    assert instance_create["instances"][0]["instance_id"] == "i-3651695"
    assert instance_create["instances"][0]["key_name"] == key_name
    assert instance_create["instances"][0]["instance_type"] == instance_type

    username = instance_create["instances"][0]["name"]
    assert username.startswith("redhat-")

    mock_boto3_session.assert_called_once()
    mock_boto3_session.return_value.resource.assert_called_once_with("ec2")
    mock_resource.create_instances.assert_called_once_with(
        ImageId=image_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=[security_group_id],
        SubnetId=subnet_id,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": f"{username}"}],
            }
        ],
        MinCount=1,
        MaxCount=1,
    )


@mock.patch("boto3.Session")
def test_create_instance_unable_create(mock_boto3_session):
    """Test unable to create an EC2 instance."""
    mock_client = mock.MagicMock()
    mock_client.create_instances.return_value = []
    mock_boto3_session.return_value.resource.return_value = mock_client

    mock_client = mock.MagicMock()
    mock_client.describe_subnets.return_value = {
        "Subnets": [{"SubnetId": "subnet-on-vpc"}]
    }
    mock_boto3_session.return_value.client.return_value = mock_client

    region = "ca-central-1"
    ec2_helper = EC2Helper(region=region)
    image_id = "rhel-10"
    instance_type = "t2.nano"
    key_name = "test-key-pair"

    instance_create = ec2_helper.create_instance(
        image_id=image_id,
        instance_type=instance_type,
        key_name=key_name,
    )

    assert instance_create["count"] == 0
    assert len(instance_create["instances"]) == 0


@mock.patch("boto3.Session")
def test_stop_instance_success(mock_boto3_session):
    """Test successful stopping of an EC2 instance."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-1234567890", "State": {"Name": "running"}}
                ]
            }
        ]
    }

    mock_client.stop_instances.return_value = {
        "StoppingInstances": [
            {
                "InstanceId": "i-1234567890",
                "CurrentState": {"Name": "stopping"},
                "PreviousState": {"Name": "running"},
            }
        ]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.stop_instance("i-1234567890")

    assert result["success"] is True
    assert result["instance_id"] == "i-1234567890"
    assert result["previous_state"] == "running"
    assert result["current_state"] == "stopping"

    mock_client.describe_instances.assert_called_once_with(InstanceIds=["i-1234567890"])
    mock_client.stop_instances.assert_called_once_with(InstanceIds=["i-1234567890"])


@mock.patch("boto3.Session")
def test_stop_instance_already_stopped(mock_boto3_session):
    """Test stopping an instance that is already stopped."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-1234567890", "State": {"Name": "stopped"}}
                ]
            }
        ]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.stop_instance("i-1234567890")

    assert result["success"] is False
    assert "already stopped" in result["error"]

    mock_client.describe_instances.assert_called_once_with(InstanceIds=["i-1234567890"])
    mock_client.stop_instances.assert_not_called()


@mock.patch("boto3.Session")
def test_stop_instance_not_found(mock_boto3_session):
    """Test stopping an instance that doesn't exist."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {"Reservations": []}

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.stop_instance("i-nonexistent")

    assert result["success"] is False
    assert "not found" in result["error"]

    mock_client.describe_instances.assert_called_once_with(
        InstanceIds=["i-nonexistent"]
    )
    mock_client.stop_instances.assert_not_called()


@mock.patch("boto3.Session")
def test_stop_instance_invalid_state(mock_boto3_session):
    """Test stopping an instance in an invalid state (e.g., terminating)."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-1234567890", "State": {"Name": "terminating"}}
                ]
            }
        ]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.stop_instance("i-1234567890")

    assert result["success"] is False
    assert "cannot be stopped" in result["error"]
    assert "terminating" in result["error"]

    mock_client.describe_instances.assert_called_once_with(InstanceIds=["i-1234567890"])
    mock_client.stop_instances.assert_not_called()


@mock.patch("boto3.Session")
def test_terminate_instance_success(mock_boto3_session):
    """Test successful termination of an EC2 instance."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-1234567890",
                        "State": {"Name": "running"},
                        "Tags": [
                            {"Key": "Name", "Value": "test-instance"},
                            {"Key": "Owner", "Value": "test-user"},
                        ],
                    }
                ]
            }
        ]
    }

    mock_client.terminate_instances.return_value = {
        "TerminatingInstances": [
            {
                "InstanceId": "i-1234567890",
                "CurrentState": {"Name": "shutting-down"},
                "PreviousState": {"Name": "running"},
            }
        ]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.terminate_instance("i-1234567890")

    assert result["success"] is True
    assert result["instance_id"] == "i-1234567890"
    assert result["instance_name"] == "test-instance"
    assert result["previous_state"] == "running"
    assert result["current_state"] == "shutting-down"

    mock_client.describe_instances.assert_called_once_with(InstanceIds=["i-1234567890"])
    mock_client.terminate_instances.assert_called_once_with(
        InstanceIds=["i-1234567890"]
    )


@mock.patch("boto3.Session")
def test_terminate_instance_already_terminated(mock_boto3_session):
    """Test terminating an instance that is already terminated."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-1234567890", "State": {"Name": "terminated"}}
                ]
            }
        ]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.terminate_instance("i-1234567890")

    assert result["success"] is False
    assert "already terminated" in result["error"]

    mock_client.describe_instances.assert_called_once_with(InstanceIds=["i-1234567890"])
    mock_client.terminate_instances.assert_not_called()


@mock.patch("boto3.Session")
def test_terminate_instance_terminating(mock_boto3_session):
    """Test terminating an instance that is already being terminated."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-1234567890", "State": {"Name": "terminating"}}
                ]
            }
        ]
    }

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.terminate_instance("i-1234567890")

    assert result["success"] is False
    assert "already being terminated" in result["error"]

    mock_client.describe_instances.assert_called_once_with(InstanceIds=["i-1234567890"])
    mock_client.terminate_instances.assert_not_called()


@mock.patch("boto3.Session")
def test_stop_instance_api_error(mock_boto3_session):
    """Test handling of AWS API errors when stopping an instance."""
    mock_client = mock.MagicMock()

    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {"InstanceId": "i-1234567890", "State": {"Name": "running"}}
                ]
            }
        ]
    }

    error_response = {
        "Error": {
            "Code": "UnauthorizedOperation",
            "Message": "You are not authorized to perform this operation.",
        }
    }
    mock_client.stop_instances.side_effect = botocore.exceptions.ClientError(
        error_response, "StopInstances"
    )

    mock_boto3_session.return_value.client.return_value = mock_client

    ec2_helper = EC2Helper(region="us-east-1")
    result = ec2_helper.stop_instance("i-1234567890")

    assert result["success"] is False
    assert "AWS API error" in result["error"]
    assert "not authorized" in result["error"]
