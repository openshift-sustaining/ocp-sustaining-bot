import boto3
from config import config
from tools.helpers import get_values_for_key_from_dict_of_parameters


class EC2Helper:
    def __init__(self, region=None):
        self.region = region or config.AWS_DEFAULT_REGION
        self.session = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

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
                "--instance-ids", params_dict
            )

            filters = []
            state_filters = get_values_for_key_from_dict_of_parameters(
                "--state", params_dict
            )
            if state_filters:
                filters.append({"Name": "instance-state-name", "Values": state_filters})

            instance_type_filters = get_values_for_key_from_dict_of_parameters(
                "--type", params_dict
            )
            if instance_type_filters:
                filters.append(
                    {"Name": "instance-type", "Values": instance_type_filters}
                )

            response = ec2.describe_instances(InstanceIds=instance_ids, Filters=filters)
        except Exception as e:
            # TODO: replace print with log error
            print(f"Unable to get instances description from AWS: {e}")
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
                        "state": instance_state_name,
                    }
                    instances_info.append(instance_info)

        # return a dictionary that contains the instances_info array and the count of server instances
        return {"count": len(instances_info), "instances": instances_info}

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
                server_name = instances[0].id
                print(f"Server {server_name} created successfully")
                server_info = {
                    "name": server_name,
                    "key_name": key_name,
                    "instance_type": instance_type,
                }
                return {
                    "count": 1,
                    "instances": [server_info],
                }
        except Exception as e:
            # TODO: replace print with log error
            print(f"An error occurred creating the EC2 instance {e}")
            raise e
