"""
Configuration for Slack Worker Service
Loads configuration from environment variables only
Independent service - no parent config dependency
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class WorkerConfig:
    """Configuration class for slack worker"""

    # Slack configuration
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")
    ROTA_GROUP_CHANNEL = os.getenv("ROTA_GROUP_CHANNEL", "")

    # Google Sheets configuration
    ROTA_SERVICE_ACCOUNT = os.getenv("ROTA_SERVICE_ACCOUNT", "")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
    ROTA_SHEET = os.getenv("ROTA_SHEET", "ROTA")
    ROTA_SYNC_WORKSHEET = os.getenv("ROTA_SYNC_WORKSHEET", "Smartsheet_Sync")
    ASSIGNMENT_WORKSHEET = os.getenv("ASSIGNMENT_WORKSHEET", "Assignments")

    # User configuration (JSON string from env)
    ROTA_USERS = {}
    ROTA_ADMINS = {}
    
    # Smartsheet configuration
    SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN", "")
    SMARTSHEET_SHEET_ID = os.getenv("SMARTSHEET_SHEET_ID", "") or os.getenv(
        "SMARTSHEET_REPORT_ID", ""
    )

    # Team members configuration
    ROTA_LEADS = (
        os.getenv("ROTA_LEADS", "").split(",") if os.getenv("ROTA_LEADS") else []
    )
    ROTA_MEMBERS = (
        os.getenv("ROTA_MEMBERS", "").split(",") if os.getenv("ROTA_MEMBERS") else []
    )

    # Job scheduling configuration (cron expressions)
    # Empty string = job disabled, non-empty = job enabled with that schedule
    SCHEDULE_ROTA_GROUP_REMINDER = os.getenv("SCHEDULE_ROTA_GROUP_REMINDER", "0 9 * * MON,THU")
    SCHEDULE_ROTA_DM_FRIDAY = os.getenv("SCHEDULE_ROTA_DM_FRIDAY", "0 17 * * FRI")
    SCHEDULE_ROTA_DM_MONDAY = os.getenv("SCHEDULE_ROTA_DM_MONDAY", "0 9 * * MON")
    SCHEDULE_ROTA_SHEET_SYNC = os.getenv("SCHEDULE_ROTA_SHEET_SYNC", "0 8 * * *")

    # File locking configuration for horizontal scaling
    LOCK_DIR = os.getenv("LOCK_DIR", "/tmp/slack_worker_locks")
    LOCK_TIMEOUT = int(os.getenv("LOCK_TIMEOUT", "300"))

    # Timezone
    TIMEZONE = os.getenv("TIMEZONE", "UTC")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = WorkerConfig()


def _parse_json_config():
    """Parse JSON configuration from environment variables"""
    import json
    
    # Parse ROTA_USERS
    rota_users_str = os.getenv("ROTA_USERS", "{}")
    try:
        config.ROTA_USERS = json.loads(rota_users_str) if rota_users_str else {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse ROTA_USERS from environment")
        config.ROTA_USERS = {}
    
    # Parse ROTA_ADMINS
    rota_admins_str = os.getenv("ROTA_ADMINS", "{}")
    try:
        config.ROTA_ADMINS = json.loads(rota_admins_str) if rota_admins_str else {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse ROTA_ADMINS from environment")
        config.ROTA_ADMINS = {}


# Parse JSON configs on module load
_parse_json_config()


def validate_config():
    """Validate that required configuration is present"""
    errors = []

    if not config.SLACK_BOT_TOKEN:
        errors.append("SLACK_BOT_TOKEN is required")

    if not config.ROTA_SERVICE_ACCOUNT:
        errors.append("ROTA_SERVICE_ACCOUNT is required")

    if config.SCHEDULE_ROTA_GROUP_REMINDER and not config.ROTA_GROUP_CHANNEL:
        errors.append("ROTA_GROUP_CHANNEL is required when group reminders are enabled")

    if config.SCHEDULE_ROTA_SHEET_SYNC:
        if not config.SMARTSHEET_ACCESS_TOKEN:
            errors.append("SMARTSHEET_ACCESS_TOKEN is required when sheet sync is enabled")
        if not config.SMARTSHEET_SHEET_ID:
            errors.append("SMARTSHEET_SHEET_ID is required when sheet sync is enabled")

    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    logger.info("Configuration validation successful")
            logger.error(error)
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    logger.info("Configuration validation successful")
