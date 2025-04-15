from aws.ec2_helper import EC2Helper
from aws.rosa_helper import ROSAHelper
from ostack.core import OpenStackHelper


# Helper function to handle the "help" command
def handle_help(say, user):
    say(
        f"Hello <@{user}>! I'm here to help. You can use the following commands:\n"
        "`create-rosa-cluster <cluster_name>`: Create an AWS OpenShift cluster.\n"
        "`create-openstack-vm <name> <image> <flavor> <network>`: Create an OpenStack VM.\n"
        "`hello`: Greet the bot."
    )


# Helper function to handle creating a ROSA cluster
def handle_create_rosa_cluster(say, user, text):
    cluster_name = text.replace("create-rosa-cluster", "").strip()
    rosa_helper = ROSAHelper(region="<provide-a-valid-region-name>")  # Set your region
    rosa_helper.create_rosa_cluster(cluster_name, say)


# Helper function to handle creating an OpenStack VM
def handle_create_openstack_vm(say, user, text):
    args = text.replace("create-openstack-vm", "").strip().split()
    os_helper = OpenStackHelper()
    os_helper.create_vm(args, say)


# Helper function to handle greeting
def handle_hello(say, user):
    say(f"Hello <@{user}>! How can I assist you today?")


# Helper function to handle creating an AWS EC2 instances
def handle_create_aws_vm(say, user):
    ec2_helper = EC2Helper(region="<provide-a-valid-region-name>")  # Set your region
    instance = ec2_helper.create_instance(
        "<provide-valid-ami-id>",  # Replace with a valid AMI ID
        "<instance-type>",  # Replace with a valid instance type
        "<ssh-login-key-pair-name>",  # Replace with your key name
        "<security-group-id>",  # Replace with your security group ID
        "<subnet-id>",  # Replace with your subnet ID
    )
    say(f"Successfully created EC2 instance: {instance.id}")


# Helper function to list AWS EC2 instances
def handle_list_aws_vms(say, region):
    ec2_helper = EC2Helper(region=region)  # Set your region
    instances_info = ec2_helper.list_instances(state_filter="running")
    if len(instances_info) == 0:
        say("There are currently no running EC2 instances to retrieve")
    else:
        for instance_info in instances_info:
            say(f"\n*** AWS EC2 VM Details ***\n{instance_info}\n")
