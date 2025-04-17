# generate a dictionary with information on the server's status
def generate_server_status_dict(is_successful, messages, server_info):
    return {
        "is_successful_creation": 1 if is_successful else 0,
        "messages": messages,
        "server_info": server_info,  # an instance of class ServerInfo if not None
    }


def get_messages_info(status_dict):
    if status_dict and isinstance(status_dict, dict):
        return status_dict.get("messages", [])
    return []


def is_server_created_ok(status_dict):
    if status_dict and isinstance(status_dict, dict):
        is_successful = status_dict.get("is_successful_creation", 0)
        return is_successful == 1
    return False


def get_field_from_server_info(field_name, status_dict):
    if status_dict and isinstance(status_dict, dict):
        server_info_instance = status_dict.get("server_info", None)
        if server_info_instance:
            return server_info_instance.get_field_value(field_name)
    return None
