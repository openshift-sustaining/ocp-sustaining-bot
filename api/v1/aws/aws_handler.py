from api.v1.cloud_services import CloudService
from sdk.aws.ec2 import EC2Helper


def aws_get_handler(service: str, type: str, state: str):
    query_dict = {}
    query_dict["state"] = state
    query_dict["type"] = type
    aws_helper = EC2Helper()
    if service == CloudService.vms:
        instances = aws_helper.list_instances(query_dict)
        return {
            "instances": instances,
            "service": service,
            "type": type,
            "state": state,
        }
