from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import config
from aws.core import ROSAHelper, AWSHelper
from ostack.core import OpenStackHelper
import re

app = App(token=config.SLACK_BOT_TOKEN)

def list_aws_ec2_instances(say):
    aws_helper = AWSHelper()
    instances_info = aws_helper.get_ec2_instances_info(state_filter="running")
    if len(instances_info) == 0:
        say("There are currently no running EC2 instances to retrieve")
    else:
        for instance_info in instances_info:
            say(f"{instance_info}")

@app.event("app_mention")
@app.event("message")
def mention_handler(body, say):
    user = body.get("event", {}).get("user")
    text = body.get("event", {}).get("text", "").strip()

    if re.search(r"\bhelp\b", text, re.IGNORECASE):
        say(
            f"Hello <@{user}>! I'm here to help. You can use the following commands:\n"
            "`create-rosa-cluster <cluster_name>`: Create an AWS OpenShift cluster.\n"
            "`create-openstack-vm <name> <image> <flavor> <network>`: Create an OpenStack VM.\n"
            "`hello`: Greet the bot."
        )
    elif text.startswith("create-rosa-cluster"):
        cluster_name = text.replace("create-rosa-cluster", "").strip()
        rosa_helper = ROSAHelper()
        rosa_helper.create_rosa_cluster(cluster_name, say)
    elif text.startswith("create-openstack-vm"):
        args = text.replace("create-openstack-vm", "").strip().split()
        os_helper = OpenStackHelper()
        os_helper.create_vm(args, say)
    elif re.search(r"\bhello\b", text, re.IGNORECASE):
        say(f"Hello <@{user}>! How can I assist you today?")
    elif re.search(r"\bcreate_aws_vm\b", text, re.IGNORECASE):
        aws_helper = AWSHelper()
        instance = aws_helper.create_instance(
            "ami-0d2614eafc1b0e4d2",
            "t2.micro",
            "prabhakar",
            "sg-0a698ca3494298d7d",
            "subnet-0ca17bcc389bf108f",
        )
        say(f"Successfuly created VM : {instance}")
    elif re.search(r"\blist_aws_vms\b", text, re.IGNORECASE):
        list_aws_ec2_instances(say)
    else:
        say(
            f"Hello <@{user}>! I couldn't understand your request. Please try again or type 'help' for assistance."
        )


# Main Entry Point
if __name__ == "__main__":
    print("Starting Slack bot...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
