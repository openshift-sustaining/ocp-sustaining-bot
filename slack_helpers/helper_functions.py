from aws.ec2_helper import EC2Helper
from helpers.general_helper import (
    is_server_created_ok,
    get_field_from_server_info,
)
from ostack.core import OpenStackHelper


# Helper function to handle the "help" command
def handle_help(say, user):
    say(
        f"Hello <@{user}>! I'm here to help. You can use the following commands:\n"
        "`create-openstack-vm <name> <image> <flavor> <network>`: Create an OpenStack VM.\n"
        "`list-aws-vms`\n"
        "`hello`: Greet the bot."
    )


# Helper function to handle creating an OpenStack VM
def handle_create_openstack_vm(say, user, text):
    try:
        args = text.replace("create-openstack-vm", "").strip().split()
        os_helper = OpenStackHelper()
        os_helper.create_vm(args)
    except Exception as e:
        say(f"An error occurred creating the openstack VM : {e}")


# Helper function to handle greeting
def handle_hello(say, user):
    say(f"Hello <@{user}>! How can I assist you today?")


# Helper function to handle creating an AWS EC2 instances
def handle_create_aws_vm(say, user, region):
    try:
        ec2_helper = EC2Helper(region=region)  # Set your region
        server_status_dict = ec2_helper.create_instance(
            "<provide-valid-ami-id>",  # Replace with a valid AMI ID
            "<instance-type>",  # Replace with a valid instance type
            "<ssh-login-key-pair-name>",  # Replace with your key name
            "<security-group-id>",  # Replace with your security group ID
            "<subnet-id>",  # Replace with your subnet ID
        )
        if server_status_dict and is_server_created_ok(server_status_dict):
            say(
                f"Successfully created EC2 instance: {get_field_from_server_info('id', server_status_dict)}"
            )
        else:
            say("Unable to create EC2 instance")
    except Exception as e:
        say(f"An error occurred creating the EC2 instance : {e}")


# Helper function to list AWS EC2 instances
def handle_list_aws_vms(say, region):
    try:
        ec2_helper = EC2Helper(region=region)  # Set your region
        instances_info = ec2_helper.list_instances(state_filter="running")
        if len(instances_info) == 0:
            say("There are currently no running EC2 instances to retrieve")
        else:
            for instance_info in instances_info:
                # TODO - format each dictionary element
                say(f"\n*** AWS EC2 VM Details ***\n{str(instance_info)}\n")
    except Exception as e:
        say(f"An error occurred listing the EC2 instances : {e}")
