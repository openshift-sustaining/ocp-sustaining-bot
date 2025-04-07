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

    def list_instances(self):
        """
        List all EC2 instances in the specified region.
        """
        ec2 = self.session.client("ec2")
        response = ec2.describe_instances()
        return response["Reservations"]

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
