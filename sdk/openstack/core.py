from openstack import connection
from config import config
import logging

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

    def list_servers(self, status_filter):
        """
        List all OpenStack VMs, optionally filtered by status (e.g., 'ACTIVE', 'SHUTOFF').
        Returns a list of dictionaries with basic VM info.
        """
        servers_info = []
        try:
            # Iterate through all servers
            print(f"[DEBUG] Filtering VMs with status: {status_filter}")
            for server in self.conn.compute.servers(status=status_filter):
                # Initialize IP-related fields
                networks = server.addresses or {}
                ip_addr, ip_version, net_name = None, None, None

                # Prioritize floating IP, fallback to fixed if not available
                for net, ips in networks.items():
                    for ip_info in ips:
                        if ip_info.get("OS-EXT-IPS:type") == "floating":
                            ip_addr = ip_info.get("addr")
                            ip_version = ip_info.get("version")
                            net_name = net
                            break
                        elif not ip_addr and ip_info.get("OS-EXT-IPS:type") == "fixed":
                            ip_addr = ip_info.get("addr")
                            ip_version = ip_info.get("version")
                            net_name = net

                # Collect server details
                servers_info.append(
                    {
                        "name": server.name,
                        "server_id": server.id,
                        "flavor": server.flavor.get("original_name")
                        or server.flavor.get("id"),
                        "availability_zone": server.availability_zone,
                        "network": net_name,
                        "ip_version": ip_version,
                        "public_ip": ip_addr,
                        "key_name": getattr(server, "key_name", "N/A"),
                        "status": server.status,
                    }
                )

            print(
                f"[OpenStackHelper] Retrieved {len(servers_info)} servers with status='{status_filter}'"
            )
            return servers_info
        except Exception as e:
            print(f"[OpenStackHelper] Error listing servers: {e}")
            return []

    def create_vm(self, args):
        """
        Create an OpenStack VM with the specified parameters provided as a list of arguments.

        :param args: List of arguments: [name, image, flavor, network]
        :return: dictionary
        """
        if len(args) != 4:
            logger.error("create-openstack-vm: Invalid parameters supplied")
            raise ValueError(
                "Invalid parameters: Usage: `create-openstack-vm <name> <image> <flavor> <network>`"
            )

        name, image, flavor, network = args

        logger.info(f"Creating OpenStack VM: {name}...")

        try:
            server = self.conn.compute.create_server(
                name=name, image=image, flavor=flavor, networks=[{"uuid": network}]
            )
            logger.info(f"VM {server.name} created successfully in OpenStack!")
            # todo: add additional information to server_info dictionary later
            server_info = {
                "name": server.name,
            }
            return {
                "count": 1,
                "instances": [server_info],
            }
        except Exception as e:
            logger.error(f"Error creating OpenStack VM: {str(e)}")
            raise e
