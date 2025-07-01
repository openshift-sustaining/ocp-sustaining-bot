import os

import pytest

pytest_plugins = [
    "pytester",
]


@pytest.fixture(scope="session", autouse=True)
def setup_environment_variables():
    os.environ["OS_IMAGE_MAP"] = '{"root": "dummy-image-id"}'
    os.environ["OS_NETWORK_MAP"] = '{"network1": "dummy-network-id"}'
    os.environ["OS_DEFAULT_NETWORK"] = "network1"
    os.environ["OS_DEFAULT_SSH_USER"] = "root"
    os.environ["OS_DEFAULT_KEY_NAME"] = "dummy-key-name"
    os.environ["RH_CA_BUNDLE_TEXT"] = "RH_CA_BUNDLE_TEXT"
    os.environ["VAULT_ENABLED_FOR_DYNACONF"] = "VAULT_ENABLED_FOR_DYNACONF"
    os.environ["VAULT_URL_FOR_DYNACONF"] = "VAULT_URL_FOR_DYNACONF"
    os.environ["VAULT_SECRET_ID_FOR_DYNACONF"] = "VAULT_SECRET_ID_FOR_DYNACONF"
    os.environ["VAULT_ROLE_ID_FOR_DYNACONF"] = "VAULT_ROLE_ID_FOR_DYNACONF"
    os.environ["VAULT_MOUNT_POINT_FOR_DYNACONF"] = "VAULT_MOUNT_POINT_FOR_DYNACONF"
    os.environ["VAULT_PATH_FOR_DYNACONF"] = "VAULT_PATH_FOR_DYNACONF"
    os.environ["VAULT_KV_VERSION_FOR_DYNACONF"] = "VAULT_KV_VERSION_FOR_DYNACONF"
