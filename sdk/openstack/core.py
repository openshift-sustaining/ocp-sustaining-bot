from openstack import connection
from openstack.exceptions import ResourceFailure, ConflictException
from config import config
from sdk.tools.helpers import get_list_of_values_for_key_in_dict_of_parameters
import logging
import traceback

logger = logging.getLogger(__name__)


class OpenStackHelper:
    def __init__(
        self,
        auth_url=None,
        project_name=None,
        application_credential_id=None,
        application_credential_secret=None,
    ):
        self.conn = connection.Connection(
            auth_url=config.OS_AUTH_URL,
            application_credential_id=config.OS_APP_CRED_ID,
            application_credential_secret=config.OS_APP_CRED_SECRET,
            region_name=config.OS_REGION_NAME,
            interface=config.OS_INTERFACE,
            identity_api_version=config.OS_ID_API_VERSION,
            auth_type=config.OS_AUTH_TYPE,
        )

    def list_servers(self, params_dict=None):
        """
        List all OpenStack VMs, optionally filtered by status (e.g., 'ACTIVE', 'SHUTOFF').
        Returns a list of dictionaries with basic VM info.
        """
        if params_dict is None:
            params_dict = {}

        try:
            # Extract status filters as a list
            status_filter = get_list_of_values_for_key_in_dict_of_parameters(
                "status", params_dict
            )

            # Default to ACTIVE if no status filter provided
            status_filter = status_filter[0].upper() if status_filter else "ACTIVE"

            servers_info = []
            # Iterate through all servers
            for server in self.conn.compute.servers(status=status_filter):
                # Initialize IP-related fields
                networks = server.addresses or {}
                ip_addr, net_name = None, None

                # Prioritize floating IP, fallback to fixed if not available
                for net, ips in networks.items():
                    for ip_info in ips:
                        if ip_info.get("OS-EXT-IPS:type") == "floating":
                            ip_addr = ip_info.get("addr")
                            net_name = net
                            break
                        elif not ip_addr and ip_info.get("OS-EXT-IPS:type") == "fixed":
                            ip_addr = ip_info.get("addr")
                            net_name = net

                # Collect server details
                servers_info.append(
                    {
                        "name": server.name,
                        "server_id": server.id,
                        "flavor": server.flavor.get("original_name")
                        or server.flavor.get("id"),
                        "network": net_name,
                        "private_ip": ip_addr,
                        "key_name": getattr(server, "key_name", "N/A"),
                        "status": server.status,
                    }
                )

            # Log the number of servers retrieved
            logger.info(
                f"Retrieved {len(servers_info)} servers with status filter '{status_filter}'."
            )
            return {"count": len(servers_info), "instances": servers_info}

        except Exception as e:
            # Log the exception that occurred during the listing process
            logger.exception(
                f"Error listing servers with status filter '{status_filter}': {e}"
            )
            raise e

    def create_servers(self, name, image_id, flavor, key_name, network=None):
        """
        Create an OpenStack VM with the specified parameters provided as a dictionary.
        :param name: Name of the VM.
        :param image_id: ID of the image to use.
        :param flavor: Flavor name (size) of the VM.
        :param key_name: Name of the SSH keypair to associate.
        :param network: (Optional) Network UUID to attach the instance to.
        :return: dictionary containing instance details.
        """

        logger.info(
            f"Creating OpenStack VM: {name} with image {image_id}, flavor {flavor}, "
            f"network {network}, key_name {key_name}"
        )

        networks_param = [{"uuid": network}] if network else []

        # Validate the provided key_name
        available_keys = [kp.name for kp in self.conn.compute.keypairs()]
        if key_name not in available_keys:
            logger.error(
                f"Invalid key_name '{key_name}' provided. Available keypairs: {available_keys}"
            )
            raise ValueError(
                f"Invalid key_name '{key_name}' provided. Available keypairs: {available_keys}"
            )

        try:
            # Resolve flavor by name
            flavor = self.conn.compute.find_flavor(flavor, ignore_missing=False)
            if not flavor:
                raise ValueError(f"Flavor '{flavor}' not found in OpenStack.")

            # Optionally validate image exists
            image = self.conn.compute.find_image(image_id, ignore_missing=False)
            if not image:
                raise ValueError(f"Image '{image_id}' not found in OpenStack.")

            server = self.conn.compute.create_server(
                name=name,
                image_id=image.id,
                flavor_id=flavor.id,
                networks=networks_param,
                key_name=key_name,
            )

            # Wait for VM to become ACTIVE
            server = self.conn.compute.wait_for_server(server)

            logger.info(f"VM {server.name} created successfully in OpenStack!")

            # Extract the first fixed (private) IP address
            private_ip = None
            for addr_list in server.addresses.values():
                for addr in addr_list:
                    if addr.get("OS-EXT-IPS:type") == "fixed":
                        private_ip = addr.get("addr")
                        break
                if private_ip:
                    break

            logger.info(f"VM {server.name} is ACTIVE with private IP: {private_ip}")

            # Construct response dictionary
            server_info = {
                "name": server.name,
                "server_id": server.id,
                "status": server.status,
                "flavor": flavor.name,
                "network": network or "Default Network",
                "key_name": key_name,
                "private_ip": private_ip or "N/A",
            }

            return {
                "count": 1,
                "instances": [server_info],
            }

        except ResourceFailure as rf:
            logger.error(f"OpenStack VM transitioned to ERROR state: {str(rf)}")
            raise RuntimeError(
                "OpenStack VM provisioning failed. Please verify image/flavor/network configuration."
            ) from rf

        except Exception as e:
            logger.error(f"Error creating OpenStack VM: {str(e)}")
            logger.error(traceback.format_exc())
            raise e

    def create_keypair(self, key_name: str):
        """
        Function to create keypair on Openstack and return the private key.
        It will default to RSA to maintain consistency with AWS
        """
        new_key = {}
        try:
            key = self.conn.create_keypair(key_name)

            new_key["KeyName"] = key_name
            new_key["KeyFingerprint"] = key["fingerprint"]
            new_key["KeyMaterial"] = key["private_key"]

            logger.debug(
                f"Created keypair {key_name} with fingerprint: {key['fingerprint']}"
            )

        except ConflictException as e:
            logger.error(f"Key already existed for this user: {e}")

        return new_key

    def delete_keypair(self, key_name: str):
        """
        Function to delete keypair on Openstack.
        Returns a boolean.
        """
        result = self.conn.delete_keypair(key_name)
        if not result:
            logger.error(f"Couldn't delete key: {key_name}")

        return result

    def describe_keypair(self, key_name: str = None):
        """
        Function to fetch keys from Openstack
        """
        key = {}
        try:
            if key_name:
                ret_keys = self.conn.list_keypairs({"name": key_name})
                if not ret_keys or not isinstance(ret_keys, list):
                    return None

                key["KeyName"] = ret_keys[0].name
                key["KeyFingerprint"] = ret_keys[0].fingerprint
            else:
                ret_keys = self.conn.list_keypairs()
                if not ret_keys or not isinstance(ret_keys, list):
                    return None

                key = ret_keys
        except Exception as e:
            logger.exception(f"Unexpected exception occurred while fetching keys: {e}")
            # Return empty key

        return key
