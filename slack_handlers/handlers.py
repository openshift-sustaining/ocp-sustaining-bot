from sdk.aws.ec2 import EC2Helper
from sdk.openstack.core import OpenStackHelper
from sdk.tools.helpers import get_dict_of_command_parameters
from dotenv import load_dotenv
import os
import logging
import traceback

# 2. Load .env
load_dotenv()

# Openstack Configuration mappings
OS_IMAGE_MAP = {
    "fedora": os.getenv("OPENSTACK_IMAGE_ID_FEDORA"),
    "ubuntu": os.getenv("OPENSTACK_IMAGE_ID_UBUNTU"),
    "centos": os.getenv("OPENSTACK_IMAGE_ID_CENTOS"),
}

NETWORK_MAP = {
    "provider_net_lab": os.getenv("OPENSTACK_NETWORK_PROVIDER_NET_LAB"),
    "provider_net_cci_5": os.getenv("OPENSTACK_NETWORK_PROVIDER_NET_CCI_5"),
}

DEFAULT_NETWORK = os.getenv("DEFAULT_NETWORK", "provider_net_cci_5")
DEFAULT_SSH_USER = os.getenv("DEFAULT_SSH_USER", "fedora")
DEFAULT_KEY_NAME = os.getenv("DEFAULT_KEY_NAME", "ocp-sust-slackbot-keypair")

#
logger = logging.getLogger(__name__)


# Helper function to handle the "help" command
def handle_help(say, user):
    try:
        logger.info(
            f"Help command invoked by user: {user}. Sending list of available commands."
        )
        say(
            f"Hello <@{user}>! Here's what I can help you with:\n\n"
            "*Available Commands:*\n"
            "`hello` - Greet the bot.\n"
            "`help` - Show this help message.\n"
            "`list-team-links` - Display important team links.\n"
            "`create-openstack-vm <name> <image> <flavor> <network>` - Create an OpenStack VM.\n"
            "`list-openstack-vms [--status=active,shutoff]` : List OpenStack VMs optionally filtered by status.\n"
            "`create-aws-vm <os_name> <instance_type> <key_pair=new,existing>` - Create an AWS EC2 instance.\n"
            "`list-aws-vms [--state=pending,running,stopped]` : List AWS VMs optionally filtered by state.\n"
        )

    except Exception as e:
        logger.error(f"Error in handle_help: {e}")


# Helper function to handle creating an OpenStack VM
def handle_create_openstack_vm(say, user, command_line):
    try:
        command_params = get_dict_of_command_parameters(command_line)

        # Extract key params from command
        name = command_params.get("name")
        os_name = command_params.get("os_name")
        flavor = command_params.get("flavor")
        key_name = command_params.get("key_name")

        logger.info(
            f"Parsed Parameters: name={name}, os_name={os_name}, flavor={flavor}, key_name={key_name}"
        )

        # Validate required fields
        required_params = ["name", "os_name", "flavor", "key_name"]
        missing_params = [
            param for param in required_params if not command_params.get(param)
        ]

        if missing_params:
            say(
                f":warning: Missing required parameters: {', '.join(missing_params)}. "
                f"Usage: create-openstack-vm --name=<name> --os_name=<os_name> --flavor=<flavor> --key_name=<key>\n"
                f"Supported OS names: {', '.join(OS_IMAGE_MAP.keys())}"
            )
            return

        # Normalize OS name and retrieve corresponding image ID
        os_name_lower = os_name.strip().lower()
        image_id = OS_IMAGE_MAP.get(os_name_lower)

        if not image_id:
            say(
                f":x: Unsupported OS name: `{os_name}`. "
                f"Supported OS names: {', '.join(OS_IMAGE_MAP.keys())}"
            )
            return

        # Resolve network ID using default network name
        network_id = NETWORK_MAP.get(DEFAULT_NETWORK)
        if not network_id:
            say(
                ":x: No valid network ID found for the default network. Please check configuration."
            )
            logger.error(f"Missing network ID for default network: {DEFAULT_NETWORK}")
            return

        logger.info(f"Using Image ID: {image_id} and Network ID: {network_id}")

        # Build request payload for OpenStackHelper
        params_dict = {
            "name": name,
            "image-id": image_id,
            "flavor": flavor,
            "key_name": key_name,
            "network": network_id,
        }

        say(
            ":hourglass_flowing_sand: Now processing your request for an OpenStack VM... Please wait."
        )
        openstack_helper = OpenStackHelper()
        response = openstack_helper.create_servers(params_dict)

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
                f"`ssh -i <path_to_your_private_key.pem> {DEFAULT_SSH_USER}@{instance_info.get('private_ip', '<Private_IP>')}`\n"
                "Make sure your key file has the correct permissions: `chmod 400 <path_to_your_private_key.pem>`\n"
                "\n\n"
                ":warning: *Key Pair Access:*\n"
                f"To access this instance via SSH, you should have the `{instance_info.get('key_name', DEFAULT_KEY_NAME)}` private key.\n"
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
def handle_list_openstack_vms(say, command_line=""):
    try:
        # Extract parameters using the utility function
        params_dict = get_dict_of_command_parameters(command_line)

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
def handle_hello(say, user):
    logger.info(f"Saying hello back to user {user}")
    say(f"Hello <@{user}>! How can I assist you today?")


def handle_create_aws_vm(say, user, region, command_line, app):
    try:
        # Parse the command parameters
        command_params = get_dict_of_command_parameters(command_line)

        os_name = command_params.get("os_name")
        instance_type = command_params.get("instance_type")
        key_pair = command_params.get("key_pair")

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
        key_pair = key_pair.strip().lower()
        if key_pair not in {"new", "existing"}:
            say(":warning: `key_pair` should be either `new` or `existing`")
            return

        # Ensure os_name is either 'Linux' or 'linux'
        if os_name.strip().lower() == "linux":
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
                key_pair, user, app, os_name, instance_type, say, ec2_helper
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
        logger.error(
            f"An error occurred while creating the EC2 instance. Command line: {command_line}"
        )
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


# Helper function to list important team links
def handle_list_team_links(say, user):
    say(
        text=".",
        blocks=helper_setup_slack_header_line(" Here are the important team links:"),
    )

    important_links = [
        ("Release Controller Page", "https://amd64.ocp.releases.ci.openshift.org/"),
        (
            "OCP Sustaining Confluence Space",
            "https://spaces.redhat.com/display/SustainingEngineering/OpenShift+Sustaining+Engineering",
        ),
        (
            "SE Operational Jira Dashboard",
            "https://issues.redhat.com/secure/Dashboard.jspa",
        ),
        (
            "OpenStack Login Page",
            "https://cloud.psi.redhat.com/dashboard/project/instances/",
        ),
        (
            "OCP SE Attendance Sheet",
            "https://docs.google.com/spreadsheets/d/108tMw1JqGE7dqOmToo7G2MfvLMtfOxdkX5OXNW0OBt4/edit?gid=585683499#gid=585683499",
        ),
        (
            "OCP Teams Tracker Sheet",
            "https://docs.google.com/spreadsheets/d/1I0wzqmkBxSmoRtSCEBUe4nXHvPLQ3K959t8VWnOhurA/edit?gid=1529539181#gid=1529539181",
        ),
    ]

    link_lines = "\n".join(
        [
            f":small_orange_diamond: *{title}:* <{url}|Link>"
            for title, url in important_links
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
    key_option, user, app, os_name, instance_type, say, cloud_sdk_obj
):
    key_to_use = {}

    existing_key = cloud_sdk_obj.describe_keypair(key_name=user)
    if existing_key:
        logger.debug(f"Found existing key: {existing_key['KeyFingerprint']}")
    else:
        logger.debug("No existing keys found.")

    if key_option == "new":
        # Delete old key since we want to maintian only one key per user (per cloud)
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
            + f"Cloud: AWS, OS: {os_name}, Instance: {instance_type}",
        )
        logger.debug("Sent private key in user DM.")

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
