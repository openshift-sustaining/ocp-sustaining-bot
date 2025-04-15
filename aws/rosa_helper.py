import subprocess
from config import config


class ROSAHelper:
    def __init__(self, region=None):
        self.region = region or config.AWS_DEFAULT_REGION

    def create_rosa_cluster(self, cluster_name, say):
        """
        Create a ROSA cluster using the ROSA CLI.
        If `say` is provided, it will send messages back to Slack.
        """
        if not cluster_name:
            if say:
                say(
                    "Please provide a cluster name. Usage: `create-aws-cluster <cluster_name>`"
                )
                return

        if say:
            say(
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
            if say:
                say(f"Cluster {cluster_name} created successfully in AWS!")
        except subprocess.CalledProcessError as e:
            if say:
                say(f"Error creating AWS cluster: {str(e)}")
            raise e

    def list_rosa_clusters(self, say=None):
        """
        List all ROSA clusters using the ROSA CLI.
        If `say` is provided, it will send the list to Slack.
        """
        if say:
            say("Fetching ROSA clusters...")

        try:
            command = ["rosa", "list", "clusters"]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            if say:
                say(f"ROSA Clusters:\n{result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            if say:
                say(f"Error fetching ROSA clusters: {str(e)}")
            raise e
