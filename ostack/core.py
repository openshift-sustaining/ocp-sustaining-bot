from openstack import connection
from config import config


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
            project_id=config.OS_PROJECT_ID,
            application_credential_id=config.OS_APP_CRED_ID,
            application_credential_secret=config.OS_APP_CRED_SECRET,
            region_name=config.OS_REGION_NAME,
            interface=config.OS_INTERFACE,
            identity_api_version=config.OS_ID_API_VERSION,
            auth_type=config.OS_AUTH_TYPE,
        )

    def list_servers(self):
        """
        List all servers in OpenStack.
        """
        return [server.name for server in self.conn.compute.servers()]

    def create_vm(self, args):
        """
        Create an OpenStack VM with the specified parameters provided as a list of arguments.

        :param args: List of arguments: [name, image, flavor, network]
        :return: dictionary
        """
        if len(args) != 4:
            # todo: replace with log error
            print(f"create-openstack-vm: Invalid parameters supplied")
            raise ValueError(
                "Invalid parameters: Usage: `create-openstack-vm <name> <image> <flavor> <network>`"
            )

        name, image, flavor, network = args

        # todo: replace with log info
        print(f"Creating OpenStack VM: {name}...")

        try:
            server = self.conn.compute.create_server(
                name=name, image=image, flavor=flavor, networks=[{"uuid": network}]
            )
            # todo: replace with log info
            print(f"VM {server.name} created successfully in OpenStack!")
            # todo: add additional information to server_info dictionary later
            server_info = {
                "name": server.name,
            }
            return {
                "count": 1,
                "instances": [server_info],
            }
        except Exception as e:
            # todo: replace with log error
            print(f"Error creating OpenStack VM: {str(e)}")
            raise e
