from sdk.aws.ec2 import EC2Helper
from sdk.openstack.core import OpenStackHelper


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


# Helper function to list OpenStack VMs with error handling
def handle_list_openstack_vms(say):
    try:
        helper = OpenStackHelper()
        servers = helper.list_servers()

        if not servers:
            say(":no_entry_sign: There are currently *no ACTIVE VMs* in OpenStack.")
            return

        result = {"count": len(servers), "instances": servers}

        say("*OpenStack ACTIVE VMs:*")
        say(f"```{result}```")

    except Exception as e:
        # Log the error for debugging purposes
        print(f"[ERROR] Failed to list OpenStack VMs: {e}")
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
        say(f"An error occurred creating the EC2 instance : {e}")


# Helper function to list AWS EC2 instances
def handle_list_aws_vms(say, region):
    try:
        ec2_helper = EC2Helper(region=region)  # Set your region
        instances_dict = ec2_helper.list_instances(state_filter="running")
        count_servers = instances_dict.get("count", 0)
        if count_servers == 0:
            say("There are currently no running EC2 instances to retrieve")
        else:
            for instance_info in instances_dict.get("instances", []):
                # TODO - format each dictionary element
                say(f"\n*** AWS EC2 VM Details ***\n{str(instance_info)}\n")
    except Exception as e:
        say(f"An error occurred listing the EC2 instances : {e}")
