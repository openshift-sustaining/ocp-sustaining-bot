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
from dotenv import load_dotenv
from dynaconf import Dynaconf

logger = logging.getLogger(__name__)

# Required environment variables for worker service
required_keys = [
    "SLACK_BOT_TOKEN",
    "ROTA_SERVICE_ACCOUNT",
    "ROTA_USERS",
    "ROTA_ADMINS",
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
with open(ca_bundle_file.name, "w") as f:
    f.write(os.getenv("RH_CA_BUNDLE_TEXT", ""))

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
    logger.warning("Vault connection failed")
except hvac.exceptions.InvalidRequest:
    logger.warning("Authentication error with Vault")

# Parse JSON configurations and convert to appropriate types
for key in dir(config):
    try:
        value = getattr(config, key)
        if isinstance(value, str):
            val = json.loads(value)
            config.set(key, val)
    except json.decoder.JSONDecodeError:
        logger.warning(f"{key} is not a valid JSON string")
        pass
    except AttributeError:
        logger.warning(f"Attribute {key} not found.")

# Set defaults for optional worker config if not in Vault/env
if not hasattr(config, "ROTA_GROUP_CHANNEL"):
    config.ROTA_GROUP_CHANNEL = os.getenv("ROTA_GROUP_CHANNEL", "")

if not hasattr(config, "SPREADSHEET_ID"):
    config.SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")

if not hasattr(config, "ROTA_SHEET"):
    config.ROTA_SHEET = os.getenv("ROTA_SHEET", "ROTA")

if not hasattr(config, "ASSIGNMENT_WSHEET"):
    config.ASSIGNMENT_WSHEET = os.getenv("ASSIGNMENT_WSHEET", "Assignments")

if not hasattr(config, "SMARTSHEET_ACCESS_TOKEN"):
    config.SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN", "")

if not hasattr(config, "ROTA_LEADS"):
    rota_leads_str = os.getenv("ROTA_LEADS", "")
    config.ROTA_LEADS = rota_leads_str.split(",") if rota_leads_str else []

if not hasattr(config, "ROTA_MEMBERS"):
    rota_members_str = os.getenv("ROTA_MEMBERS", "")
    config.ROTA_MEMBERS = rota_members_str.split(",") if rota_members_str else []

if not hasattr(config, "SCHEDULE_ROTA_NOTIFICATIONS"):
    config.SCHEDULE_ROTA_NOTIFICATIONS = os.getenv(
        "SCHEDULE_ROTA_NOTIFICATIONS", "0 9 * * MON,THU"
    )

if not hasattr(config, "SCHEDULE_ROTA_SHEET_SYNC"):
    config.SCHEDULE_ROTA_SHEET_SYNC = os.getenv(
        "SCHEDULE_ROTA_SHEET_SYNC", "0 8 * * MON,THU"
    )

if not hasattr(config, "LOCK_DIR"):
    config.LOCK_DIR = os.getenv("LOCK_DIR", "/tmp/slack_worker_locks")

if not hasattr(config, "LOCK_TIMEOUT"):
    config.LOCK_TIMEOUT = int(os.getenv("LOCK_TIMEOUT", "300"))

if not hasattr(config, "TIMEZONE"):
    config.TIMEZONE = os.getenv("TIMEZONE", "UTC")

if not hasattr(config, "LOG_LEVEL"):
    config.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """Validate that required configuration is present"""
    errors = []

    if not hasattr(config, "SLACK_BOT_TOKEN") or not config.SLACK_BOT_TOKEN:
        errors.append("SLACK_BOT_TOKEN is required")

    if not hasattr(config, "ROTA_SERVICE_ACCOUNT") or not config.ROTA_SERVICE_ACCOUNT:
        errors.append("ROTA_SERVICE_ACCOUNT is required")

    if (
        hasattr(config, "SCHEDULE_ROTA_NOTIFICATIONS")
        and config.SCHEDULE_ROTA_NOTIFICATIONS
    ):
        if not hasattr(config, "ROTA_GROUP_CHANNEL") or not config.ROTA_GROUP_CHANNEL:
            errors.append(
                "ROTA_GROUP_CHANNEL is required when notifications are enabled"
            )

    if hasattr(config, "SCHEDULE_ROTA_SHEET_SYNC") and config.SCHEDULE_ROTA_SHEET_SYNC:
        if (
            not hasattr(config, "SMARTSHEET_ACCESS_TOKEN")
            or not config.SMARTSHEET_ACCESS_TOKEN
        ):
            errors.append(
                "SMARTSHEET_ACCESS_TOKEN is required when sheet sync is enabled"
            )

    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    logger.info("Configuration validation successful")
