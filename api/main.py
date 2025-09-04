from fastapi import FastAPI
from api.router.aws_router import router as aws_router


def create_api() -> FastAPI:
    app = FastAPI(title="ocp-sustaining-bot API", version="1.0.0")
    app.include_router(router=aws_router, prefix="/aws")
    return app


app = create_api()
