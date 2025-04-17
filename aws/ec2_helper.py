import boto3
from config import config
from helpers.general_helper import generate_server_status_dict
from helpers.server_info import ServerInfo, ServerType


class EC2Helper:
    def __init__(self, region=None):
        self.region = region or config.AWS_DEFAULT_REGION
        self.session = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    def list_instances(self, state_filter="running"):
        """
        get all EC2 instances in the specified region.
        returns a list of dictionary items describing each EC2 instance whose instance_state matches the
        state_filter
        if there are no EC2 instances, an empty list is returned
        TODO: use the filter in the AWS call
        """
        try:
            ec2 = self.session.client("ec2")
            response = ec2.describe_instances()
        except Exception as e:
            print(f"Unable to get instances description from AWS: {e}")
            return []

        instances_info = []

        if response:
            reservations = response.get("Reservations", [])
            try:
                for reservation in reservations:
                    for instance in reservation.get("Instances", []):
                        instance_state_name = instance.get("State", {}).get("Name", "")

                        # Apply the state filter (default is 'running')
                        # TO DO: use a filter above in the call to ec2.describe_instances()
                        if state_filter and instance_state_name != state_filter:
                            continue  # Skip this instance if it doesn't match the filter

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
                            "state": instance_state_name,
                        }
                        instances_info.append(instance_info)
            except Exception as e:
                print(f"An error occurred parsing EC2 instance information: {e}")
        return instances_info

    def create_instance(
        self, image_id, instance_type, key_name, security_group_id, subnet_id
    ):
        """
        Create an EC2 instance with the given parameters.
        """
        ec2 = self.session.resource("ec2")
        try:
            instance_params = {
                "ImageId": image_id,
                "InstanceType": instance_type,
                "KeyName": key_name,
                "SecurityGroupIds": [security_group_id],
                "MinCount": 1,
                "MaxCount": 1,
            }
            if subnet_id:
                instance_params["SubnetId"] = subnet_id

            instances = ec2.create_instances(**instance_params)
            if instances and len(instances > 0):
                server_name = instances[0].instance_id
                messages = ["Server created successfully"]
                server_info = ServerInfo(
                    server_name,
                    ServerType.AWS_EC2_INSTANCE,
                    True,
                    instances[0],
                    messages,
                )
                return generate_server_status_dict(True, messages, server_info)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
