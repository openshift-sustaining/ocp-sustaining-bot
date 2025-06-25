import os

import pytest

pytest_plugins = [
    "pytester",
]


@pytest.fixture(scope="session", autouse=True)
def setup_environment_variables():
    os.environ["SLACK_BOT_TOKEN"] = "SLACK_BOT_TOKEN"
    os.environ["SLACK_APP_TOKEN"] = "SLACK_APP_TOKEN"
    os.environ["AWS_ACCESS_KEY_ID"] = "AWS_ACCESS_KEY_ID"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "AWS_SECRET_ACCESS_KEY"
    os.environ["AWS_DEFAULT_REGION"] = "AWS_DEFAULT_REGION"
    os.environ["OS_AUTH_URL"] = "OS_AUTH_URL"
    os.environ["OS_PROJECT_ID"] = "OS_PROJECT_ID"
    os.environ["OS_INTERFACE"] = "OS_INTERFACE"
    os.environ["OS_ID_API_VERSION"] = "OS_ID_API_VERSION"
    os.environ["OS_REGION_NAME"] = "OS_REGION_NAME"
    os.environ["OS_APP_CRED_ID"] = "OS_APP_CRED_ID"
    os.environ["OS_APP_CRED_SECRET"] = "OS_APP_CRED_SECRET"
    os.environ["OS_AUTH_TYPE"] = "v3applicationcredential"
    os.environ["ALLOW_ALL_WORKSPACE_USERS"] = "ALLOW_ALL_WORKSPACE_USERS"
    os.environ["ALLOWED_SLACK_USERS"] = "ALLOWED_SLACK_USERS"
    os.environ["OS_IMAGE_MAP"] = '{"root": "dummy-image-id"}'
    os.environ["OS_NETWORK_MAP"] = '{"network1": "dummy-network-id"}'
    os.environ["OS_DEFAULT_NETWORK"] = "network1"
    os.environ["OS_DEFAULT_SSH_USER"] = "root"
    os.environ["OS_DEFAULT_KEY_NAME"] = "dummy-key-name"
