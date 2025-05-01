from sdk.aws.ec2 import EC2Helper
from sdk.openstack.core import OpenStackHelper
from sdk.tools.helpers import get_dict_of_command_parameters
import logging

logger = logging.getLogger(__name__)


# Helper function to handle the "help" command
def handle_help(say, user):
    logger.debug(
        f"Help command invoked by user: {user}. Sending list of available commands."
    )
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
        logger.error(f"An error occurred creating the openstack VM : {e}")
        say("An internal error occurred, please contact administrator.")


# Helper function to list OpenStack VMs with error handling
def handle_list_openstack_vms(say, command_text=""):
    try:
        # Default to ACTIVE if nothing passed
        status_filter = "ACTIVE"
        args = command_text.strip().split()

        if not args:
            status_filter = "ACTIVE"

        # Check for named argument like --status=shutoff
        for arg in args:
            if arg.startswith("--status="):
                status_filter = arg.split("=", 1)[1].upper()
                break

        # Log the status filter being used
        logger.info(f"Filtering OpenStack VMs with status filter: {status_filter}.")

        helper = OpenStackHelper()
        servers = helper.list_servers(status_filter=status_filter)

        # Check for error returned from main function
        if "error" in servers:
            say(f":warning: {servers['error']}")
            return

        if servers["count"] == 0:
            say(
                f":no_entry_sign: There are currently no VMs in the *{status_filter}* state in OpenStack."
            )
            return

        say(f"*OpenStack {status_filter} VMs:*")
        say(f"```{servers}```")

    except Exception as e:
        # Log the error for debugging purposes
        logger.error(f"Failed to list OpenStack VMs: {e}")
        say(":x: An error occurred while fetching the list of VMs.")


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
        if server_status_dict:
            servers_created = server_status_dict.get("instances", [])
            if len(servers_created) == 1:
                say(
                    f"Successfully created EC2 instance: {servers_created[0].get('name', 'unknown')}"
                )
        else:
            say("Unable to create EC2 instance")
    except Exception as e:
        logger.error(f"An error occurred creating the EC2 instance: {e}")
        say("An internal error occurred, please contact administrator.")


# Helper function to list AWS EC2 instances
def handle_list_aws_vms(say, region, user, command_line):
    try:
        params_dict = get_dict_of_command_parameters(command_line)

        ec2_helper = EC2Helper(region=region)  # Set your region
        instances_dict = ec2_helper.list_instances(params_dict)
        count_servers = instances_dict.get("count", 0)
        if count_servers == 0:
            msg = (
                "There are currently no EC2 instances available that match the specified criteria"
                if len(params_dict) > 0
                else "There are currently no EC2 instances to retrieve"
            )
            say(msg)
        else:
            for instance_info in instances_dict.get("instances", []):
                # TODO - format each dictionary element
                say(f"\n*** AWS EC2 VM Details ***\n{str(instance_info)}\n")
    except Exception as e:
        logger.error(f"An error occurred listing the EC2 instances: {e}")
        say("An internal error occurred, please contact administrator.")
