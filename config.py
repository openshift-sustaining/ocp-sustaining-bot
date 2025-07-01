import logging
import os
from dotenv import load_dotenv, dotenv_values
from dynaconf import Dynaconf
import tempfile
import json

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

# Load CA Cert to avoid SSL errors
load_dotenv()
ca_bundle_file = tempfile.NamedTemporaryFile()
with open(ca_bundle_file.name, "w") as f:
    f.write(os.getenv("RH_CA_BUNDLE_TEXT"))

try:
    config = Dynaconf(
        load_dotenv=True,  # This will load config from `.env`
        environment=False,  # This will disable layered env
        vault_enabled=True,
        vault={
            "url": os.environ["VAULT_URL_FOR_DYNACONF"],
            "verify": ca_bundle_file.name,
        },
        envvar_prefix=False,  # This will make it so that ALL the variables from `.env` are loaded
    )
except:
    # Blanket exception to cover multiple exceptions like vault not found or authentication failure
    logging.warn("Vault connection failed")

for key in dir(config):
    try:
        value = getattr(config, key)
        if isinstance(value, str):
            val = json.loads(value)
            # NOTE: This will create a `Dynabox` object which is basically a wrapper around dicts which allows . access to keys
            # So you can access `config.key.val` instead of `config.key['val']` but it can be used like a dictionary as well.
            config.set(key, val)
    except json.decoder.JSONDecodeError:
        pass
    except AttributeError:
        logging.warn(f"Attribute {key} not found.")  # Should usually be harmless

# Verify that all keys were loaded correctly
for k in required_keys:
    if not hasattr(config, k):
        logging.error(f"Could not read key: {k} from Vault.")
        raise AttributeError(f"Could not read key: {k} from Vault.")
