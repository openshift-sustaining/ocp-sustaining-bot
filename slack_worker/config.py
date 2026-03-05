"""
Configuration for Slack Worker Service
Uses Dynaconf + Vault pattern (same as root config.py) but only with worker-needed env vars
"""

import json
import logging
import os
import tempfile

import httpx
import hvac
import requests.exceptions
from dotenv import load_dotenv
from dynaconf import Dynaconf

required_keys = [
    "SLACK_BOT_TOKEN",
    "ROTA_SERVICE_ACCOUNT",
    "ROTA_USERS",
    "ROTA_ADMINS",
    "LOCK_DIR",
    "TIMEZONE",
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

# DON'T MOVE: `basicConfig` gets called only once. Dynaconf sets it to `WARNING` so our setting should be above that
log_level = os.getenv("LOG_LEVEL", "INFO")
log_level = log_level.upper()
log_level_int = getattr(logging, log_level, 20)
log_format = "[%(asctime)s %(levelname)s %(name)s] %(message)s"
logging.basicConfig(level=log_level_int, format=log_format)

vault_enabled = req_env_vars <= set(os.environ.keys())  # subset of os.environ

# Load CA Cert to avoid SSL errors
ca_bundle_file = tempfile.NamedTemporaryFile()
cert_txt = os.getenv("RH_CA_BUNDLE_TEXT", "")
cert_text_final = cert_txt.replace("\\n", "\n")
with open(ca_bundle_file.name, "w") as f:
    f.write(cert_text_final)

config = Dynaconf(
    load_dotenv=True,
    environment=False,
    vault_enabled=vault_enabled,
    vault={
        "url": os.getenv("VAULT_URL_FOR_DYNACONF", ""),
        "verify": ca_bundle_file.name,
    },
    envvar_prefix=False,
)

# Dynaconf is lazy -- vault connection happens on first access (dir/getattr),
# not at construction time. Catch vault errors here where they actually occur.
try:
    for key in dir(config):
        try:
            value = getattr(config, key)
            if isinstance(value, str):
                val = json.loads(value)
                config.set(key, val)
        except json.decoder.JSONDecodeError:
            logging.debug(f"{key} is not a valid JSON string.")
        except AttributeError:
            logging.debug(f"Attribute {key} not found.")
except (
    httpx.ConnectError,
    ConnectionError,
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
):
    logging.warning("Vault connection failed — continuing with env/dotenv config only")
    config = Dynaconf(load_dotenv=True, environment=False, vault_enabled=False, envvar_prefix=False)
except hvac.exceptions.InvalidRequest:
    logging.warning("Vault authentication error — continuing with env/dotenv config only")
    config = Dynaconf(load_dotenv=True, environment=False, vault_enabled=False, envvar_prefix=False)

# Verify that all keys were loaded correctly
for k in required_keys:
    if not hasattr(config, k):
        logging.error(f"Could not read key: {k} from Vault.")
        raise AttributeError(f"Could not read key: {k} from Vault.")
