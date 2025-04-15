import boto3
from config import config


class EC2Helper:
    def __init__(self, region=None):
        self.region = region or config.AWS_DEFAULT_REGION
        self.session = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    def list_instances(self, state_filter = "running"):
        """
        get all EC2 instances in the specified region.
        returns a list of formatted strings describing each EC2 instance whose instance_state matches the
        state_filter
        if there are no EC2 instances, an empty list is returned
        """
        try:
            ec2 = self.session.client("ec2")
            response = ec2.describe_instances()
        except Exception as e:
            print(f"Unable to get instances description from AWS: {e}")
            return []

        instances_info = []

        if response and response.get("Reservations"):
            reservations = response["Reservations"]
            try:
                if len(reservations) == 0:
                    return []
                for reservation in reservations:
                    for instance in reservation["Instances"]:
                        instance_state = instance["State"]["Name"]

                        # Apply the state filter (default is 'running')
                        if state_filter and instance_state != state_filter:
                            continue  # Skip this instance if it doesn't match the filter

                        # Tags is a list and each element in the list is a dictionary
                        ec2_instance_name = ""
                        ec2_architecture = ""
                        for tag in instance['Tags']:
                            key = tag.get('Key')
                            if key == 'Name':
                                ec2_instance_name = tag['Value']
                            elif key == 'architecture':
                                ec2_architecture  = tag['Value']
                        # Create a formatted string with instance details
                        instance_info = (
                            f"Instance Name: {ec2_instance_name}\n"
                            f"Architecture: {ec2_architecture}\n"
                            f"ID: {instance.get('InstanceId')}\n"
                            f"Image ID: {instance.get('ImageId')}\n"
                            f"Instance type: {instance.get('InstanceType')}\n"
                            f"Key name: {instance.get('KeyName')}\n"
                            f"VPC ID: {instance.get('VpcId')}\n"
                            f"Public IP: {instance.get('PublicIpAddress', 'N/A')}\n"
                            f"State: {instance_state}"
                        )
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
            return instances[0]
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
