from sdk.aws.ec2 import EC2Helper
from sdk.openstack.core import OpenStackHelper
from config import config
from sdk.tools.help_system import (
    command_meta,
    handle_help_command,
    get_openstack_os_names,
    get_openstack_statuses,
    get_openstack_flavors,
    get_aws_instance_states,
    get_aws_instance_types,
)
import logging
import traceback


logger = logging.getLogger(__name__)


# Helper function to handle the "help" command
@command_meta(
    name="help",
    description="Show help information for commands",
    arguments={
        "command": {
            "description": "Specific command to get help for",
            "required": False,
            "type": "str",
        }
    },
    examples=["help", "help create-openstack-vm"],
)
def handle_help(say, user, command_name=None):
    """Handle help command using the new help system."""
    handle_help_command(say, user, command_name)


# Helper function to handle creating an OpenStack VM
@command_meta(
    name="create-openstack-vm",
    description="Create an OpenStack VM with specified configuration",
    arguments={
        "name": {"description": "Name for the VM", "required": True, "type": "str"},
        "os_name": {
            "description": "Operating system name",
            "required": True,
            "type": "str",
            "choices": get_openstack_os_names,
        },
        "flavor": {
            "description": "VM flavor/size (e.g., ci.cpu.small)",
            "required": True,
            "type": "str",
            "choices": get_openstack_flavors,
        },
        "key_pair": {
            "description": "Whether to use new or existing keypair",
            "required": True,
            "type": "str",
        },
    },
    examples=[
        "create-openstack-vm --name=myvm --os_name=fedora --flavor=ci.cpu.small --key_pair=new|existing"
    ],
)
def handle_create_openstack_vm(say, user, params_dict):
    try:
        if not isinstance(params_dict, dict):
            raise ValueError(
                "Invalid parameter params_dict passed to handle_create_openstack_vm"
            )

        # Extract key params from command
        name = params_dict.get("name")
        os_name = params_dict.get("os_name")
        flavor = params_dict.get("flavor")
        key_pair = params_dict.get("key_pair")  # `new` or `existing`

        logger.info(
            f"Parsed Parameters: name={name}, os_name={os_name}, flavor={flavor}, key_pair={key_pair}"
        )

        # Validate required fields
        required_params = ["name", "os_name", "flavor", "key_pair"]
        missing_params = [
            param for param in required_params if not params_dict.get(param)
        ]

        if missing_params:
            say(
                f":warning: Missing required parameters: {', '.join(missing_params)}. "
                f"Usage: create-openstack-vm --name=<name> --os_name=<os_name> --flavor=<flavor> --key_pair=<new,existing>\n"
                f"Supported OS names: {', '.join(config.OS_IMAGE_MAP.keys())}"
            )
            return

        # Normalize OS name and retrieve corresponding image ID
        os_name_lower = os_name.strip().lower() if os_name else ""
        image_id = config.OS_IMAGE_MAP.get(os_name_lower)

        if not image_id:
            say(
                f":x: Unsupported OS name: `{os_name}`. "
                f"Supported OS names: {', '.join(config.OS_IMAGE_MAP.keys())}"
            )
            return

        # Resolve network ID using default network name
        network_id = config.OS_NETWORK_MAP.get(config.OS_DEFAULT_NETWORK)
        if not network_id:
            say(
                ":x: No valid network ID found for the default network. Please check configuration."
            )
            logger.error(
                f"Missing network ID for default network: {config.OS_DEFAULT_NETWORK}"
            )
            return

        logger.info(f"Using Image ID: {image_id} and Network ID: {network_id}")

        say(
            ":hourglass_flowing_sand: Now processing your request for an OpenStack VM... Please wait."
        )
        openstack_helper = OpenStackHelper()

        key_pair = _helper_select_keypair(
            key_pair, user, app, "OpenStack", image_id, flavor, say, openstack_helper
        )

        response = openstack_helper.create_servers(
            name, image_id, flavor, key_pair["KeyName"], network_id
        )

        # Extract result from response
        instances = response.get("instances", [])
        if instances:
            instance_info = instances[0]

            say(":white_check_mark: *Successfully created OpenStack VM!*\n")

            # Format and display instance metadata as table
            print_keys = [
                "name",
                "server_id",
                "key_name",
                "flavor",
                "network",
                "status",
                "private_ip",
            ]
            block_message = "Here are the details of your new OpenStack VM:"
            helper_display_dict_output_as_table(
                {"instances": [instance_info]}, print_keys, say, block_message
            )

            # Provide SSH access instructions for user
            say(
                f"\n\n"
                ":key: *Access Instructions (Linux/Unix):*\n"
                "Use the following command to SSH into your instance:\n"
                f"`ssh -i <path_to_your_private_key.pem> {config.OS_DEFAULT_SSH_USER}@{instance_info.get('private_ip', '<Private_IP>')}`\n"
                "Make sure your key file has the correct permissions: `chmod 400 <path_to_your_private_key.pem>`\n"
                "\n\n"
                ":warning: *Key Pair Access:*\n"
                f"To access this instance via SSH, you should have the private key with fingerprint `{key_pair['KeyFingerprint']}`.\n"
                "If you don't have it, please contact the admin for access."
            )

        else:
            say(":x: VM creation failed. No instance details returned.")
            logger.error(f"OpenStack VM creation failed: {response}")

    except Exception as e:
        logger.error(f"Error during OpenStack VM creation: {e}")
        logger.error(traceback.format_exc())
        say(
            ":x: An internal error occurred while creating the OpenStack VM. Please contact the administrator."
        )


# Helper function to list OpenStack VMs with error handling
@command_meta(
    name="list-openstack-vms",
    description="List OpenStack VMs with optional status filtering",
    arguments={
        "status": {
            "description": "Filter VMs by status",
            "required": False,
            "type": "str",
            "choices": get_openstack_statuses,
            "default": "ACTIVE",
        }
    },
    examples=[
        "list-openstack-vms",
        "list-openstack-vms --status=ACTIVE",
        "list-openstack-vms --status=SHUTOFF",
    ],
)
def handle_list_openstack_vms(say, params_dict):
    try:
        if not isinstance(params_dict, dict):
            raise ValueError(
                "Invalid parameter params_dict passed to handle_list_openstack_vms"
            )

        # Define valid status filters
        VALID_STATUSES = {"ACTIVE", "SHUTOFF", "ERROR"}
        # Default to ACTIVE if no status filter provided
        status_filter = params_dict.get("status", "ACTIVE").upper()

        if status_filter not in VALID_STATUSES:
            logger.error(f"Received unsupported status filter: {status_filter}.")
            say(
                f":warning: Invalid status filter *{status_filter}*. Supported values are: {', '.join(sorted(VALID_STATUSES))}"
            )
            return

        # Log the status filter being used
        logger.info(f"Filtering OpenStack VMs with status filter: {status_filter}.")

        helper = OpenStackHelper()
        servers = helper.list_servers(params_dict)

        # Check for error returned from main function
        if "error" in servers:
            say(f":warning: {servers['error']}")
            return

        if servers["count"] == 0:
            say(
                f":no_entry_sign: There are currently no VMs in the *{status_filter}* state in OpenStack."
            )
            return
        else:
            # Define the keys to display in the table output
            print_keys = [
                "server_id",
                "name",
                "flavor",
                "network",
                "private_ip",
                "key_name",
                "status",
            ]
            # Display the data as a Slack table
            helper_display_dict_output_as_table(
                servers,
                print_keys,
                say,
                block_message=" Here are the requested VM instances:",
            )

    except Exception as e:
        # Log the error for debugging purposes
        logger.error(f"Failed to list OpenStack VMs: {e}")
        say(":x: An error occurred while fetching the list of VMs.")


# Helper function to handle greeting
@command_meta(name="hello", description="Greet the bot", examples=["hello"])
def handle_hello(say, user):
    logger.info(f"Saying hello back to user {user}")
    say(f"Hello <@{user}>! How can I assist you today?")


@command_meta(
    name="create-aws-vm",
    description="Create an AWS EC2 instance",
    arguments={
        "os_name": {
            "description": "Operating system name",
            "required": True,
            "type": "str",
            "choices": ["linux"],
        },
        "instance_type": {
            "description": "EC2 instance type",
            "required": True,
            "type": "str",
            "choices": get_aws_instance_types,
        },
        "key_pair": {
            "description": "Key pair option",
            "required": True,
            "type": "str",
            "choices": ["new", "existing"],
        },
    },
    examples=[
        "create-aws-vm --os_name=linux --instance_type=t2.micro --key_pair=new",
        "create-aws-vm --os_name=linux --instance_type=t3.small --key_pair=existing",
    ],
)
def handle_create_aws_vm(say, user, region, app, params_dict):
    try:
        if not isinstance(params_dict, dict):
            raise ValueError(
                "Invalid parameter params_dict passed to handle_create_aws_vm"
            )

        os_name = params_dict.get("os_name")
        instance_type = params_dict.get("instance_type")
        key_pair = params_dict.get("key_pair")

        # Log the parsed parameters for debugging purposes
        logger.info(
            f"Parsed Parameters: os_name={os_name}, instance_type={instance_type}, key_pair={key_pair}"
        )

        # Check for missing parameters and inform the user which ones are missing
        if not all([os_name, instance_type, key_pair]):
            missing_params = []
            if not os_name:
                missing_params.append("os_name")
            if not instance_type:
                missing_params.append("instance_type")
            if not key_pair:
                missing_params.append("key_pair")

            say(
                f":warning: Missing required parameters: {', '.join(missing_params)}. Usage: create-aws-vm --os_name=<os> --instance_type=<type> --key_pair=<key>"
            )
            return

        # Key pair should be either 'new' or 'existing'
        key_pair = key_pair.strip().lower() if key_pair else ""
        if key_pair not in {"new", "existing"}:
            say(":warning: `key_pair` should be either `new` or `existing`")
            return

        # Ensure os_name is either 'Linux' or 'linux'
        if os_name and os_name.strip().lower() == "linux":
            logger.info(f"Operating System selected: {os_name}")

            # Use the hardcoded AMI ID for Amazon Linux
            ami_id = (
                "ami-0402e56c0a7afb78f"  # Replace with actual AMI ID for your region
            )
            logger.info(f"Using AMI ID: {ami_id}")
            say(
                ":hourglass_flowing_sand: Now processing your request for a Linux Instance... Please wait."
            )

            # Create EC2 instance using the helper
            ec2_helper = EC2Helper(region=region)

            # Select key to use
            key_to_use = _helper_select_keypair(
                key_pair, user, app, "AWS", os_name, instance_type, say, ec2_helper
            )

            if not key_to_use:
                logger.error("Aborting VM creation because returned keypair was empty.")
                return

            server_status_dict = ec2_helper.create_instance(
                ami_id,  # AMI ID for Amazon Linux
                instance_type,  # Instance type (e.g., t2.micro)
                key_to_use["KeyName"],  # Key pair (e.g., your_key_pair_name)
            )

            # Log the server creation response for debugging
            logger.debug(f"Server creation response: {server_status_dict}")

            # Handle known error if server creation fails
            if "error" in server_status_dict:
                error_msg = server_status_dict["error"]
                logger.error(f"EC2 instance creation failed: {error_msg}")
                say(":x: *EC2 instance creation failed.*")
                return

            # Check for successful instance creation and provide details
            servers_created = server_status_dict.get("instances", [])
            if servers_created:
                instance = servers_created[0]

                instance_dict = {
                    "instances": [
                        {
                            "name": instance.get("name", "unknown"),
                            "instance_id": instance.get("instance_id", "unknown"),
                            "key_name": instance.get("key_name", "unknown"),
                            "instance_type": instance.get("instance_type", "unknown"),
                            "public_ip": instance.get("public_ip", "unknown"),
                        }
                    ]
                }

                # Define the keys to display in the table
                print_keys = [
                    "name",
                    "instance_id",
                    "key_name",
                    "instance_type",
                    "public_ip",
                ]

                say(":white_check_mark: *Successfully created EC2 instance!*\n\n")

                # Use the helper function to display the instance details as a table
                helper_display_dict_output_as_table(
                    instance_dict,
                    print_keys,
                    say,
                    block_message=" Here are the requested VM instances:",
                )

                say(
                    "\n\n"
                    ":key: *Access Instructions (Linux/Unix):*\n"
                    "Use the following command to SSH into your instance:\n"
                    "`ssh -i <path_to_your_private_key.pem> ec2-user@<Public_IP>`\n"
                    "Make sure your key file has the correct permissions: `chmod 400 <path_to_your_private_key.pem>`\n"
                    "\n\n"
                    ":warning: *Key Pair Access:*\n"
                    f"To access this instance via SSH, you should have the private key with fingerprint: `{key_to_use['KeyFingerprint']}`.\n"
                    "If you don't have it, please contact the admin for access."
                )
            else:
                say(":x: *EC2 instance creation failed.* No instance returned.")
                logger.error("EC2 creation failed: No instance returned in response.")
        else:
            say(f":x: Unsupported OS name: `{os_name}`. Only `Linux` is supported.")
            return

    except Exception as e:
        # Log the error and provide a user-friendly message
        logger.error("An error occurred while creating the EC2 instance")
        logger.error(f"Error Details: {e}")
        logger.error(traceback.format_exc())
        say(
            ":x: An internal error occurred while creating the EC2 instance. Please contact the administrator."
        )


def helper_create_table(data_rows, table_column_names, max_column_widths):
    """
    Given
     1. data_rows - a list of row data to display
     2. column_names - the column names in the table to display
     3. max_column_widths - a dictionary with the max column width for each column of values
    Create a table of data with spaces as padding and using a monospaced font (inside triple backticks)
    """

    # Format table header (first row) and the divider (2nd row)
    header = " | ".join(
        f"{column_name:<{max_column_widths[column_name]}}"
        for column_name in table_column_names
    )
    divider = "-+-".join(
        "-" * max_column_widths[column_name] for column_name in table_column_names
    )

    # Format the data rows, left aligning with spaces
    rows = []

    for row in data_rows:
        row_values = []
        for index, val in enumerate(row):
            # left-align the text with spaces
            row_values.append(
                f"{str(val):<{max_column_widths[table_column_names[index]]}}"
            )
        rows.append(" | ".join(row_values))

    table = "\n".join([header, divider] + rows)
    return f"```\n{table}\n```"


def helper_setup_slack_header_line(header_text, emoji_name="ledger"):
    """
    sets up a slack block consisting of an emoji and bold text. This is typically used for a header line
    """
    return [
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {"type": "emoji", "name": f"{emoji_name}"},
                        {
                            "type": "text",
                            "text": f"{header_text}",
                            "style": {"bold": True},
                        },
                    ],
                }
            ],
        }
    ]


def helper_display_dict_output_as_table(instances_dict, print_keys, say, block_message):
    """
    given a dictionary containing instance information for servers, set up a header line and then display the data in
    a "table"
    """
    if instances_dict and isinstance(instances_dict, dict) and len(instances_dict) > 0:
        say(
            text=".",
            blocks=helper_setup_slack_header_line(block_message),
        )
        max_column_widths = {}
        rows = []

        # for each column of data (including the column header name), calculate the max width of each columns data
        # storing it in a dictionary

        # initially set the max length for each column to the column header name
        for data_key_name in print_keys:
            max_column_widths[data_key_name] = len(data_key_name)

        for instance_info in instances_dict.get("instances", []):
            row = []
            for data_key_name in print_keys:
                column_value_raw = instance_info.get(data_key_name, "unknown")
                column_value = str(column_value_raw)
                current_max_len = max_column_widths.get(data_key_name, 0)
                if len(column_value) > current_max_len:
                    max_column_widths[data_key_name] = len(column_value)
                row.append(column_value)
            rows.append(row)
        say(helper_create_table(rows, print_keys, max_column_widths))


# Helper function to list AWS EC2 instances
@command_meta(
    name="list-aws-vms",
    description="List AWS EC2 instances with optional filtering",
    arguments={
        "state": {
            "description": "Filter instances by state",
            "required": False,
            "type": "str",
            "choices": get_aws_instance_states,
        },
        "type": {
            "description": "Filter instances by type",
            "required": False,
            "type": "str",
            "choices": get_aws_instance_types,
        },
        "instance-ids": {
            "description": "Comma-separated list of instance IDs",
            "required": False,
            "type": "str",
        },
    },
    examples=[
        "list-aws-vms",
        "list-aws-vms --state=running,stopped",
        "list-aws-vms --type=t2.micro,t3.small",
        "list-aws-vms --instance-ids=i-123456,i-789012",
    ],
)
def handle_list_aws_vms(say, region, user, params_dict):
    try:
        if not isinstance(params_dict, dict):
            raise ValueError(
                "Invalid parameter params_dict passed to handle_list_aws_vms"
            )

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
            print_keys = [
                "instance_id",
                "name",
                "instance_type",
                "state",
                "public_ip",
                "private_ip",
            ]
            helper_display_dict_output_as_table(
                instances_dict,
                print_keys,
                say,
                block_message=" Here are the requested VM instances:",
            )
    except Exception as e:
        logger.error(f"An error occurred listing the EC2 instances: {e}")
        say("An internal error occurred, please contact administrator.")


@command_meta(
    name="aws-modify-vm",
    description="Stop or delete AWS EC2 instances",
    arguments={
        "vm-id": {
            "description": "Instance ID to modify",
            "required": True,
            "type": "str",
        },
        "stop": {"description": "Stop the instance", "required": False, "type": "bool"},
        "delete": {
            "description": "Delete the instance",
            "required": False,
            "type": "bool",
        },
    },
    examples=[
        "aws-modify-vm --stop --vm-id=i-1234567890abcdef0",
        "aws-modify-vm --delete --vm-id=i-1234567890abcdef0",
    ],
)
def handle_aws_modify_vm(say, region, user, params_dict):
    """
    Helper function to modify AWS EC2 instances (stop/delete)
    """
    try:
        if not isinstance(params_dict, dict):
            raise ValueError(
                "Invalid parameter params_dict passed to handle_aws_modify_vm"
            )

        stop_action = params_dict.get("stop", False)
        delete_action = params_dict.get("delete", False)
        vm_id = params_dict.get("vm-id")

        if not vm_id:
            say(
                ":warning: Missing required parameter `--vm-id`. Usage: `aws-modify-vm --stop --vm-id=<id>` or `aws-modify-vm --delete --vm-id=<id>`"
            )
            return

        if not stop_action and not delete_action:
            say(":warning: You must specify either `--stop` or `--delete` action.")
            return

        if stop_action and delete_action:
            say(
                ":warning: Please specify only one action: either `--stop` or `--delete`, not both."
            )
            return

        ec2_helper = EC2Helper(region=region)

        if stop_action:
            logger.info(f"User {user} requested to stop instance {vm_id}")
            say(f":hourglass_flowing_sand: Attempting to stop instance `{vm_id}`...")

            result = ec2_helper.stop_instance(vm_id)

            if result["success"]:
                say(
                    f":white_check_mark: *Successfully initiated stop for instance `{vm_id}`*\n"
                    f"• Previous state: `{result['previous_state']}`\n"
                    f"• Current state: `{result['current_state']}`\n"
                    f"\n:information_source: The instance will take a moment to fully stop."
                )
            else:
                logger.error(
                    f"Failed to stop instance `{vm_id}`, error: {result['error']}"
                )
                say(f":x: *Failed to stop instance `{vm_id}`*")

        elif delete_action:
            logger.info(f"User {user} requested to terminate instance {vm_id}")

            say(
                f":warning: *Termination Warning*\n"
                f"You are about to permanently terminate instance `{vm_id}`. This action cannot be undone.\n"
                f":hourglass_flowing_sand: Proceeding with termination..."
            )

            result = ec2_helper.terminate_instance(vm_id)

            if result["success"]:
                instance_name = result.get("instance_name", "N/A")
                say(
                    f":white_check_mark: *Successfully initiated termination for instance `{vm_id}`*\n"
                    f"• Instance name: `{instance_name}`\n"
                    f"• Previous state: `{result['previous_state']}`\n"
                    f"• Current state: `{result['current_state']}`\n"
                    f"\n:information_source: The instance is being terminated and will be permanently deleted."
                )
            else:
                logger.error(
                    f"Failed to terminate instance `{vm_id}`, error: {result['error']}"
                )
                say(f":x: *Failed to terminate instance `{vm_id}`*")

    except Exception as e:
        logger.error(f"An error occurred while modifying EC2 instance: {e}")
        logger.error(traceback.format_exc())
        say(
            ":x: An internal error occurred while modifying the EC2 instance. Please contact the administrator."
        )


# Helper function to list important team links
@command_meta(
    name="list-team-links",
    description="Display important team links",
    examples=["list-team-links"],
)
def handle_list_team_links(say, user):
    say(
        text=".",
        blocks=helper_setup_slack_header_line(" Here are the important team links:"),
    )

    link_lines = "\n".join(
        [
            f":small_orange_diamond: *{title}:* <{url}|Link>"
            for title, url in config.USEFUL_PROJECT_LINKS.items()
        ]
    )

    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": link_lines,
                },
            },
        ],
    )


def _helper_select_keypair(
    key_option, user, app, cloud_type, os_name, instance_type, say, cloud_sdk_obj
):
    key_to_use = {}

    existing_key = cloud_sdk_obj.describe_keypair(key_name=user)
    if existing_key:
        logger.debug(f"Found existing key: {existing_key['KeyFingerprint']}")
    else:
        logger.debug("No existing keys found.")

    if key_option == "new":
        # Delete old key since we want to maintain only one key per user (per cloud)
        if existing_key:
            success = cloud_sdk_obj.delete_keypair(key_name=user)
            if not success:
                say("Some error occurred while deleting old key.")
                return
            logger.debug("Deleted old key.")

        new_key = cloud_sdk_obj.create_keypair(key_name=user)
        logger.debug(f"Created new key: {new_key['KeyFingerprint']}")

        # DM user with private key
        app.client.chat_postMessage(
            channel=user,
            text=f"New key created:\n```{new_key['KeyMaterial']}```\n"
            + f"Cloud: {cloud_type}, OS: {os_name}, Instance: {instance_type}",
        )
        logger.debug("Sent private key in user DM.")
        say("Please check DM for the newly generated private key.")

        key_to_use = {
            "KeyName": new_key["KeyName"],
            "KeyFingerprint": new_key["KeyFingerprint"],
        }

        return key_to_use

    else:
        if not existing_key:
            logger.debug("Existing key not found")
            say(":warning: You do not have any existing keys.")
            return

        key_to_use = existing_key
        logger.debug(f"Using existing key: {key_to_use['KeyFingerprint']}")

        return key_to_use
