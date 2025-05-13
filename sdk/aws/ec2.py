import boto3
from config import config
from sdk.tools.helpers import get_values_for_key_from_dict_of_parameters
import logging
import random
import string
import traceback

logger = logging.getLogger(__name__)


class EC2Helper:
    def __init__(self, region=None):
        self.region = region or config.AWS_DEFAULT_REGION
        self.session = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )
        logger.info(f"Region set for session: {self.region}")

    def list_instances(self, params_dict=None):
        """
        get all EC2 instances in the specified region.
        returns a dictionary with information on server instances
        """
        if params_dict is None:
            params_dict = {}
        try:
            ec2 = self.session.client("ec2")

            # instance ids to retrieve
            instance_ids = get_values_for_key_from_dict_of_parameters(
                "instance-ids", params_dict
            )

            filters = []
            state_filters = get_values_for_key_from_dict_of_parameters(
                "state", params_dict
            )
            if state_filters:
                filters.append({"Name": "instance-state-name", "Values": state_filters})

            instance_type_filters = get_values_for_key_from_dict_of_parameters(
                "type", params_dict
            )
            if instance_type_filters:
                filters.append(
                    {"Name": "instance-type", "Values": instance_type_filters}
                )

            response = ec2.describe_instances(InstanceIds=instance_ids, Filters=filters)
        except Exception as e:
            logger.error(f"Unable to get instances description from AWS: {e}")
            raise e

        instances_info = []

        if response:
            reservations = response.get("Reservations", [])
            for reservation in reservations:
                for instance in reservation.get("Instances", []):
                    instance_state_name = instance.get("State", {}).get("Name", "")

                    # Tags is a list and each element in the list is a dictionary
                    ec2_instance_name = ""
                    ec2_architecture = ""
                    for tag in instance.get("Tags", []):
                        key = tag.get("Key", "")
                        value = tag.get("Value", "")
                        if key == "Name":
                            ec2_instance_name = value
                        elif key == "architecture":
                            ec2_architecture = value

                    # Create a formatted string with instance details
                    instance_info = {
                        "name": ec2_instance_name,
                        "architecture": ec2_architecture,
                        "instance_id": instance.get("InstanceId", ""),
                        "image_id": instance.get("ImageId", ""),
                        "instance_type": instance.get("InstanceType", ""),
                        "key_name": instance.get("KeyName", ""),
                        "vpc_id": instance.get("VpcId", ""),
                        "public_ip": instance.get("PublicIpAddress", "N/A"),
                        "private_ip": instance.get("PrivateIpAddress", "N/A"),
                        "state": instance_state_name,
                    }
                    instances_info.append(instance_info)

        # return a dictionary that contains the instances_info array and the count of server instances
        return {"count": len(instances_info), "instances": instances_info}

    def _get_custom_vpc_id(self, vpc_name="openshift-sustaining-vpc"):
        """
        Get the custom VPC ID based on the VPC Name or Tag.
        """
        ec2_client = self.session.client("ec2")

        try:
            # Describe VPCs and filter by Name tag (or any other criteria)
            response = ec2_client.describe_vpcs(
                Filters=[{"Name": "tag:Name", "Values": [vpc_name]}]
            )
            vpcs = response.get("Vpcs", [])
            if not vpcs:
                raise Exception(f"No VPC found with name/tag '{vpc_name}'.")

            return vpcs[0]["VpcId"]
        except Exception as e:
            logger.error(f"Error fetching custom VPC ID: {e}")
            raise

    def _get_subnet_ids(self, vpc_id):
        """
        Get the subnet IDs associated with the given VPC.
        """
        ec2_client = self.session.client("ec2")

        try:
            # Describe subnets in the VPC
            response = ec2_client.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )
            if not response["Subnets"]:
                raise Exception(f"No subnets found for VPC '{vpc_id}'.")

            # Extract subnet IDs from the response
            subnet_ids = [subnet["SubnetId"] for subnet in response["Subnets"]]
            logger.info(f"Found subnets: {subnet_ids}")  # Log the subnets found
            return subnet_ids

        except Exception as e:
            logger.error(f"Error fetching subnet IDs: {e}")
            raise

    def _get_security_group_id(self, sec_group_name):
        """
        Get the security group ID for the VPC.
        """
        ec2_client = self.session.client("ec2")

        try:
            # Describe security groups in the VPC
            response = ec2_client.describe_security_groups(
                Filters=[{"Name": "tag:Name", "Values": [sec_group_name]}]
            )
            security_groups = response["SecurityGroups"]

            if not security_groups:
                raise Exception(
                    f"No security group found with name '{sec_group_name}'."
                )

            sg_id = security_groups[0]["GroupId"]
            logger.info(
                f"Found Security Group: {sg_id}"
            )  # Log the security group found
            return sg_id

        except Exception as e:
            logger.error(f"Error fetching security group ID: {e}")
            raise  # This ensures the error is raised and traceback is preserved

    def create_instance(self, image_id, instance_type, key_name):
        """
        Create an EC2 instance with the given parameters.
        """
        try:
            # Get the username for tagging
            sts = boto3.client("sts")
            identity = sts.get_caller_identity()
            arn = identity["Arn"]
            username = (
                arn.split("/")[-1]
                + "-"
                + "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
            )

            ec2_resource = self.session.resource("ec2")

            # Dynamically fetch the custom VPC ID for the region
            vpc_id = self._get_custom_vpc_id()
            if not vpc_id:
                logger.error("No VPC ID found.")
                return {"count": 0, "instances": [], "error": "No VPC ID found."}

            # Fetch subnet
            subnet_ids = self._get_subnet_ids(vpc_id)
            if not subnet_ids:
                logger.warning("No subnets found in the specified VPC")
                return {"count": 0, "instances": [], "error": "No subnets found."}
            subnet_id = random.choice(subnet_ids)

            # Fetch security group
            security_group_id = self._get_security_group_id(sec_group_name="Allow SSH")
            if not security_group_id:
                logger.error("No Security Groups found.")
                return {
                    "count": 0,
                    "instances": [],
                    "error": "No Security Group found with name Allow SSH.",
                }

            # Define instance parameters
            instance_params = {
                "ImageId": image_id,
                "InstanceType": instance_type,
                "KeyName": key_name,
                "SecurityGroupIds": [security_group_id],
                "SubnetId": subnet_id,
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": f"{username}"}],
                    }
                ],
                "MinCount": 1,
                "MaxCount": 1,
            }

            # Now create the EC2 instance using the defined parameters
            instances = ec2_resource.create_instances(**instance_params)

            if not instances:
                logger.warning(f"Unable to create EC2 instance: {instance_params}")
                return {
                    "count": 0,
                    "instances": [],
                    "error": "EC2 instance creation returned no instances. This could be due to invalid parameters, lack of capacity, or AWS service issues.",
                }

            instance = instances[0]
            instance.wait_until_running()
            instance.reload()

            logger.info(
                f"Instance {instance.id} created successfully with name '{username}'"
            )

            instance_info = {
                "name": username,
                "instance_id": instance.id,
                "key_name": key_name,
                "instance_type": instance_type,
                "public_ip": instance.public_ip_address,
            }

            return {
                "count": 1,
                "instances": [instance_info],
            }

        except Exception as e:
            logger.error(f"An error occurred creating the EC2 instance: {e}")
            logger.debug(traceback.format_exc())
            return {
                "count": 0,
                "instances": [],
                "error": str(e),
            }
