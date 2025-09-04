from fastapi import APIRouter
from api.v1.aws.aws_handler import aws_get_handler

router = APIRouter()


@router.get("/{service}")
def aws_router(service: str, type: str, state: str):
    if service == "vms":
        return aws_get_handler(service=service, type=type, state=state)
