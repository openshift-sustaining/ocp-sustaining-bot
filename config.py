import logging
import os
from dotenv import load_dotenv
from dynaconf import Dynaconf
import tempfile

required_keys = [
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "OS_AUTH_URL",
    "OS_PROJECT_ID",
    "OS_INTERFACE",
    "OS_ID_API_VERSION",
    "OS_REGION_NAME",
    "OS_APP_CRED_ID",
    "OS_APP_CRED_SECRET",
    "OS_AUTH_TYPE",
    "ALLOW_ALL_WORKSPACE_USERS",
    "ALLOWED_SLACK_USERS",
]

load_dotenv()
ca_bundle_file = tempfile.NamedTemporaryFile()
with open(ca_bundle_file.name, "w") as f:
    f.write(os.getenv("RH_CA_BUNDLE_TEXT"))

config = Dynaconf(
    load_dotenv=True,
    environment=False,
    settings_files=["settings.toml", ".secrets.toml"],
    vault_enabled=True,
    vault={"url": "https://vault.corp.redhat.com:8200/", "verify": ca_bundle_file.name},
)

# Verify that all keys were loaded correctly
for k in required_keys:
    if not hasattr(config, k):
        logging.error(f"Could not read key: {k} from Vault.")
        raise AttributeError(f"Could not read key: {k} from Vault.")
