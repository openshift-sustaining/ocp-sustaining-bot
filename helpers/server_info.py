from enum import Enum


class ServerType(Enum):
    UNKNOWN_SERVER_TYPE = (0,)
    AWS_EC2_INSTANCE = (100,)
    OPENSTACK_INSTANCE = (200,)
    AZURE_INSTANCE = (300,)
    GCP_INSTANCE = 400


class ServerInfo:
    """
    contains information on a server
    """

    def __init__(
        self, server_name, server_type, is_created_ok, server_info, info_messages
    ):
        self.server_name = server_name if server_name else "unknown server name"

        # True or False
        self.is_created_ok = is_created_ok if is_created_ok else False

        # server_info is the result of the call to the SDK to create the instance, it should be stored as a dict
        self.server_info = server_info if server_info else None

        # any messages associated with the server e.g. during the creation phase
        self.info_messages = info_messages if info_messages else []

        # ServerType(Enum) - see above
        self.server_type = (
            server_type if server_type else ServerType.UNKNOWN_SERVER_TYPE
        )

    def get_info_messages(self):
        return self.info_messages

    def is_created_ok(self):
        return self.is_created_ok

    def get_server_name(self):
        return self.server_name

    def get_field_value(self, field_name):
        if self.server_info and isinstance(self.server_info, dict):
            return self.server_info.get(field_name, None)
        return None

    def get_server_info_as_str(self):
        # TODO: this function will change to return information based on the ServerType enum etc
        return str(self.server_info)
