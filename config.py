import logging
import os
from dotenv import load_dotenv
from dynaconf import Dynaconf
import tempfile
import json
import httpx
import hvac

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
    "ROTA_SERVICE_ACCOUNT",
    "ROTA_ADMINS",
    "ROTA_USERS",
]

load_dotenv()
req_env_vars = {
    "RH_CA_BUNDLE_TEXT",
    "VAULT_ENABLED_FOR_DYNACONF",
    "VAULT_URL_FOR_DYNACONF",
    "VAULT_SECRET_ID_FOR_DYNACONF",
    "VAULT_ROLE_ID_FOR_DYNACONF",
    "VAULT_MOUNT_POINT_FOR_DYNACONF",
    "VAULT_PATH_FOR_DYNACONF",
    "VAULT_KV_VERSION_FOR_DYNACONF",
}

vault_enabled = req_env_vars <= set(os.environ.keys())  # subset of os.environ

# Load CA Cert to avoid SSL errors
ca_bundle_file = tempfile.NamedTemporaryFile()
cert_txt=os.getenv("RH_CA_BUNDLE_TEXT", "")
cert_text_final = cert_txt.replace("\\n", "\n")
with open(ca_bundle_file.name, "w") as f:
    f.write(cert_text_final)

# print("CA bundle file:", ca_bundle_file.name)
# os.system(f"cat  {ca_bundle_file.name}")


try:
    config = Dynaconf(
        load_dotenv=True,  # This will load config from `.env`
        environment=False,  # This will disable layered env
        vault_enabled=vault_enabled,
        vault={
            "url": os.getenv("VAULT_URL_FOR_DYNACONF", ""),
            "verify": ca_bundle_file.name,
        },
        envvar_prefix=False,  # This will make it so that ALL the variables from `.env` are loaded
    )
except (httpx.ConnectError, ConnectionError):
    logging.warn("Vault connection failed")
except hvac.exceptions.InvalidRequest:
    logging.warn("Authentication error with Vault")

for key in dir(config):
    try:
        value = getattr(config, key)
        if isinstance(value, str):
            val = json.loads(value)
            # NOTE: This will create a `Dynabox` object which is basically a wrapper around dicts which allows . access to keys
            # So you can access `config.key.val` instead of `config.key['val']` but it can be used like a dictionary as well.
            config.set(key, val)
    except json.decoder.JSONDecodeError:
        logging.warn(f"{key} is not a valid JSON string .")
        pass
    except AttributeError:
        logging.warn(f"Attribute {key} not found.")  # Should usually be harmless

# Verify that all keys were loaded correctly
for k in required_keys:
    if not hasattr(config, k):
        logging.error(f"Could not read key: {k} from Vault.")
        raise AttributeError(f"Could not read key: {k} from Vault.")
