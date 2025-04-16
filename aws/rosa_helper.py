import subprocess
from config import config


class ROSAHelper:
    def __init__(self, region=None):
        self.region = region or config.AWS_DEFAULT_REGION

    def create_rosa_cluster(self, cluster_name):
        """
        Create a ROSA cluster using the ROSA CLI.
        Returns a list of messages indicating the status of the operation
        """
        messages = []
        if not cluster_name:
            messages.append(
                "Please provide a cluster name. Usage: `create-aws-cluster <cluster_name>`"
            )
            return messages

        messages.append(
            f"Creating AWS OpenShift cluster: {cluster_name} in region {self.region}..."
        )

        try:
            command = [
                "rosa",
                "create",
                "cluster",
                "--cluster-name",
                cluster_name,
                "--region",
                self.region,
            ]
            subprocess.run(command, check=True)
            messages.append(f"Cluster {cluster_name} created successfully in AWS!")
            return messages
        except subprocess.CalledProcessError as e:
            print(f"Error creating AWS cluster: {str(e)}")
            raise e

    def list_rosa_clusters(self):
        """
        Build a list all ROSA clusters using the ROSA CLI.
        Returns a tuple of 1. list of messages indicating the status of the operation, 2. result.stdout
        """
        messages = ["Fetching ROSA clusters..."]

        try:
            command = ["rosa", "list", "clusters"]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            messages.append(f"ROSA Clusters:\n{result.stdout}")
            return messages, result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error fetching ROSA clusters: {str(e)}")
            raise e
