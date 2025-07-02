import unittest.mock as mock
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
