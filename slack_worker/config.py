"""
Configuration for Slack Worker Service
Standalone configuration using Dynaconf - independent from main bot config
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

# Required keys for slack_worker to function
required_keys = [
    "SLACK_BOT_TOKEN",
    "ROTA_SERVICE_ACCOUNT",
    "ROTA_USERS",
]

load_dotenv()

# Check if Vault is configured
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

# Load CA Cert to avoid SSL errors (for Vault)
ca_bundle_file = tempfile.NamedTemporaryFile(delete=False)
with open(ca_bundle_file.name, "w") as f:
    f.write(os.getenv("RH_CA_BUNDLE_TEXT", ""))

try:
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
except (httpx.ConnectError, ConnectionError):
    logger.warning("Vault connection failed")
    config = Dynaconf(load_dotenv=True, environment=False, envvar_prefix=False)
except hvac.exceptions.InvalidRequest:
    logger.warning("Authentication error with Vault")
    config = Dynaconf(load_dotenv=True, environment=False, envvar_prefix=False)

# Parse JSON strings into objects (same logic as main config)
for key in dir(config):
    try:
        value = getattr(config, key)
        if isinstance(value, str):
            val = json.loads(value)
            config.set(key, val)
    except json.decoder.JSONDecodeError:
        pass
    except AttributeError:
        pass

# Verify required keys are loaded
for k in required_keys:
    if not hasattr(config, k):
        logger.error(f"Could not read key: {k}")
        raise AttributeError(f"Could not read key: {k}")


class WorkerConfig:
    """Configuration class for slack worker with defaults and validation"""

    # Core Slack configuration (from Dynaconf/env)
    SLACK_BOT_TOKEN = getattr(config, "SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN = getattr(config, "SLACK_APP_TOKEN", "")

    # Google Sheets configuration
    ROTA_SERVICE_ACCOUNT = getattr(config, "ROTA_SERVICE_ACCOUNT", {})
    ROTA_SHEET = getattr(config, "ROTA_SHEET", "ROTA")
    ROTA_SYNC_WORKSHEET = getattr(config, "ROTA_SYNC_WORKSHEET", "Smartsheet_Sync")
    ASSIGNMENT_WORKSHEET = getattr(config, "ASSIGNMENT_WSHEET", "Assignments")

    # User mappings (from Dynaconf/env as JSON)
    ROTA_USERS = getattr(config, "ROTA_USERS", {})
    ROTA_ADMINS = getattr(config, "ROTA_ADMINS", [])

    # Smartsheet configuration
    SMARTSHEET_ACCESS_TOKEN = getattr(config, "SMARTSHEET_ACCESS_TOKEN", "")
    SMARTSHEET_SHEET_ID = getattr(
        config, "SMARTSHEET_SHEET_ID", ""
    ) or getattr(config, "SMARTSHEET_REPORT_ID", "")

    # Slack channel/user configuration
    ROTA_GROUP_CHANNEL = getattr(config, "ROTA_GROUP_CHANNEL", "")

    # Team members configuration
    _rota_leads = getattr(config, "ROTA_LEADS", "")
    ROTA_LEADS = _rota_leads.split(",") if isinstance(_rota_leads, str) and _rota_leads else _rota_leads if isinstance(_rota_leads, list) else []

    _rota_members = getattr(config, "ROTA_MEMBERS", "")
    ROTA_MEMBERS = _rota_members.split(",") if isinstance(_rota_members, str) and _rota_members else _rota_members if isinstance(_rota_members, list) else []

    # ROTA Job scheduling configuration (cron expressions)
    # Set to empty string "" to disable a job
    # Default schedules:
    # - ROTA Group reminders: Monday and Thursday at 9 AM
    # - ROTA DM reminders: Friday at 5 PM (previous week) and Monday at 9 AM (current week)
    # - ROTA Sheet sync: Disabled by default (requires Smartsheet credentials)
    SCHEDULE_ROTA_GROUP_REMINDER = getattr(config, "SCHEDULE_ROTA_GROUP_REMINDER", "0 9 * * MON,THU")
    SCHEDULE_ROTA_DM_FRIDAY = getattr(config, "SCHEDULE_ROTA_DM_FRIDAY", "0 17 * * FRI")
    SCHEDULE_ROTA_DM_MONDAY = getattr(config, "SCHEDULE_ROTA_DM_MONDAY", "0 9 * * MON")
    SCHEDULE_ROTA_SHEET_SYNC = getattr(config, "SCHEDULE_ROTA_SHEET_SYNC", "")  # "" Disabled by default

    # File locking configuration for horizontal scaling
    LOCK_DIR = getattr(config, "LOCK_DIR", "/tmp/slack_worker_locks")
    LOCK_TIMEOUT = int(getattr(config, "LOCK_TIMEOUT", "300"))

    # Timezone
    TIMEZONE = getattr(config, "TIMEZONE", "UTC")

    # Logging
    LOG_LEVEL = getattr(config, "LOG_LEVEL", "INFO")

    # Helper properties to check if ROTA jobs are enabled (non-empty schedule = enabled)
    @property
    def is_rota_group_reminder_enabled(self):
        return bool(self.SCHEDULE_ROTA_GROUP_REMINDER)

    @property
    def is_rota_dm_reminder_enabled(self):
        return bool(self.SCHEDULE_ROTA_DM_FRIDAY or self.SCHEDULE_ROTA_DM_MONDAY)

    @property
    def is_rota_sheet_sync_enabled(self):
        return bool(self.SCHEDULE_ROTA_SHEET_SYNC)


worker_config = WorkerConfig()


def validate_config():
    """Validate that required configuration is present"""
    errors = []

    if not worker_config.SLACK_BOT_TOKEN:
        errors.append("SLACK_BOT_TOKEN is required")

    if not worker_config.ROTA_SERVICE_ACCOUNT:
        errors.append("ROTA_SERVICE_ACCOUNT is required")

    # Validate ROTA group reminder dependencies
    if worker_config.is_rota_group_reminder_enabled and not worker_config.ROTA_GROUP_CHANNEL:
        errors.append("ROTA_GROUP_CHANNEL is required when SCHEDULE_ROTA_GROUP_REMINDER is set")

    # Validate ROTA sheet sync dependencies
    if worker_config.is_rota_sheet_sync_enabled:
        if not worker_config.SMARTSHEET_ACCESS_TOKEN:
            errors.append("SMARTSHEET_ACCESS_TOKEN is required when SCHEDULE_ROTA_SHEET_SYNC is set")
        if not worker_config.SMARTSHEET_SHEET_ID:
            errors.append("SMARTSHEET_SHEET_ID is required when SCHEDULE_ROTA_SHEET_SYNC is set")

    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    logger.info("Configuration validation successful")
