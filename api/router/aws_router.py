from fastapi import APIRouter
from api.aws.aws_service import aws_get_service

router = APIRouter()


@router.get("/{service}")
def aws_router(service: str, type: str, state: str):
    if service == "vms":
        return aws_get_service(service=service, type=type, state=state)
