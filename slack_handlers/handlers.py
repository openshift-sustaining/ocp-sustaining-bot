from sdk.aws.ec2 import EC2Helper
from sdk.openstack.core import OpenStackHelper
from sdk.tools.helpers import get_dict_of_command_parameters
import logging
import pandas as pd


logger = logging.getLogger(__name__)


# Helper function to handle the "help" command
def handle_help(say, user):
    logger.info(
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
def handle_list_openstack_vms(say, command_line=""):
    try:
        # Extract parameters using the utility function
        params_dict = get_dict_of_command_parameters(command_line)

        # Define valid status filters
        VALID_STATUSES = {"ACTIVE", "SHUTOFF"}
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


def format_aligned_table(df):
    """
    Given a pandas dataframe df with column names and data, create a format aligned table of data with spaces as padding
    and using a monospaced font (inside triple backticks)
    """
    if df and isinstance(df, pd.DataFrame) and not df.empty:
        # Convert all columns to string and determine max width per column
        col_widths = {
            col: max(df[col].astype(str).map(len).max(), len(col)) for col in df.columns
        }

        # Format header
        header = " | ".join(f"{col:<{col_widths[col]}}" for col in df.columns)
        divider = "-+-".join("-" * col_widths[col] for col in df.columns)

        # Format rows
        rows = []
        for _, row in df.iterrows():
            # left-align the text with a width of col_widths[col] spaces
            row_str = " | ".join(
                f"{str(val):<{col_widths[col]}}" for col, val in row.items()
            )
            rows.append(row_str)
        table = "\n".join([header, divider] + rows)
        return f"```\n{table}\n```"
    return ""


def setup_slack_header_line(header_text, emoji_name="ledger"):
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


def setup_slack_list_vms(instances_dict):
    """
    Given instances_dict which is a dictionary with information on server instances, transfer the data to a Pandas
    dataframe and then call format_aligned_table to generate a table containing this data
    """
    if instances_dict and isinstance(instances_dict, dict):
        vms_df = pd.DataFrame(
            columns=[
                "Instance Id",
                "Name",
                "Flavor",
                "State",
                "Public IP",
                "Private IP",
            ]
        )
        for instance_info in instances_dict.get("instances", []):
            row = [
                instance_info.get("instance_id", "unknown"),
                instance_info.get("name", "unknown"),
                instance_info.get("instance_type", "unknown"),
                instance_info.get("state", "unknown"),
                instance_info.get("public_ip", "unknown"),
                instance_info.get("private_ip", "unknown"),
            ]
            vms_df.loc[len(vms_df)] = row
        return format_aligned_table(vms_df)
    return ""


def display_list_vms_in_slack(instances_dict, say):
    """
    given a dictionary containing instance information for servers, setup a header line and then display the data in
    a "table"
    """
    if instances_dict and isinstance(instances_dict, dict) and len(instances_dict) > 0:
        say(
            text=".",
            blocks=setup_slack_header_line(" Here are the requested VM instances:"),
        )
        say(setup_slack_list_vms(instances_dict))


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
            display_list_vms_in_slack(instances_dict, say)
    except Exception as e:
        logger.error(f"An error occurred listing the EC2 instances: {e}")
        say("An internal error occurred, please contact administrator.")
