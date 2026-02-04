"""
Configuration for Slack Worker Service
Loads configuration from environment variables and parent config
"""

import logging
import os

# Load parent config
import sys
from datetime import datetime

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import config as parent_config

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class WorkerConfig:
    """Configuration class for slack worker"""

    # Inherit from parent config
    SLACK_BOT_TOKEN = parent_config.SLACK_BOT_TOKEN
    SLACK_APP_TOKEN = parent_config.SLACK_APP_TOKEN
    ROTA_SERVICE_ACCOUNT = parent_config.ROTA_SERVICE_ACCOUNT
    ROTA_USERS = parent_config.ROTA_USERS
    ROTA_ADMINS = parent_config.ROTA_ADMINS

    # Worker-specific configuration
    # Smartsheet configuration
    SMARTSHEET_SOURCE_URL = os.getenv(
        "SMARTSHEET_SOURCE_URL",
        "https://app.smartsheet.com/b/publish?EQBCT=970c5ff6c67a4ca7a153e3a6ef993e77",
    )
    SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN", "")
    # Accept either SMARTSHEET_SHEET_ID or SMARTSHEET_REPORT_ID
    SMARTSHEET_SHEET_ID = os.getenv("SMARTSHEET_SHEET_ID", "") or os.getenv(
        "SMARTSHEET_REPORT_ID", ""
    )

    # Google Sheets configuration
    ROTA_SHEET = getattr(parent_config, "ROTA_SHEET", "ROTA")
    ROTA_SYNC_WORKSHEET = os.getenv("ROTA_SYNC_WORKSHEET", "Smartsheet_Sync")
    ASSIGNMENT_WORKSHEET = getattr(parent_config, "ASSIGNMENT_WSHEET", "Assignments")

    # Slack channel/user configuration
    ROTA_GROUP_CHANNEL = os.getenv(
        "ROTA_GROUP_CHANNEL", ""
    )  # Channel ID for group notifications

    # Team members configuration (from env vars)
    ROTA_LEADS = (
        os.getenv("ROTA_LEADS", "").split(",") if os.getenv("ROTA_LEADS") else []
    )
    ROTA_MEMBERS = (
        os.getenv("ROTA_MEMBERS", "").split(",") if os.getenv("ROTA_MEMBERS") else []
    )

    # Job scheduling configuration (cron expressions)
    # Default schedules:
    # - Group reminders: Monday and Thursday at 9 AM
    # - DM reminders: Friday at 5 PM (previous week) and Monday at 9 AM (current week)
    # - Sheet sync: Every day at 8 AM
    SCHEDULE_GROUP_REMINDER = os.getenv("SCHEDULE_GROUP_REMINDER", "0 9 * * MON,THU")
    SCHEDULE_DM_REMINDER_FRIDAY = os.getenv(
        "SCHEDULE_DM_REMINDER_FRIDAY", "0 17 * * FRI"
    )
    SCHEDULE_DM_REMINDER_MONDAY = os.getenv(
        "SCHEDULE_DM_REMINDER_MONDAY", "0 9 * * MON"
    )
    SCHEDULE_SHEET_SYNC = os.getenv("SCHEDULE_SHEET_SYNC", "0 8 * * *")

    # File locking configuration for horizontal scaling
    LOCK_DIR = os.getenv("LOCK_DIR", "/tmp/slack_worker_locks")
    LOCK_TIMEOUT = int(os.getenv("LOCK_TIMEOUT", "300"))  # 5 minutes

    # Enable/disable specific jobs
    ENABLE_GROUP_REMINDER = os.getenv("ENABLE_GROUP_REMINDER", "true").lower() == "true"
    ENABLE_DM_REMINDER = os.getenv("ENABLE_DM_REMINDER", "true").lower() == "true"
    ENABLE_SHEET_SYNC = os.getenv("ENABLE_SHEET_SYNC", "true").lower() == "true"

    # Timezone
    TIMEZONE = os.getenv("TIMEZONE", "UTC")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = WorkerConfig()


# Validate required configuration
def validate_config():
    """Validate that required configuration is present"""
    errors = []

    if not config.SLACK_BOT_TOKEN:
        errors.append("SLACK_BOT_TOKEN is required")

    if not config.ROTA_SERVICE_ACCOUNT:
        errors.append("ROTA_SERVICE_ACCOUNT is required")

    if config.ENABLE_GROUP_REMINDER and not config.ROTA_GROUP_CHANNEL:
        errors.append("ROTA_GROUP_CHANNEL is required when group reminders are enabled")

    if config.ENABLE_SHEET_SYNC:
        if not config.SMARTSHEET_ACCESS_TOKEN:
            errors.append(
                "SMARTSHEET_ACCESS_TOKEN is required when sheet sync is enabled"
            )
        if not config.SMARTSHEET_SHEET_ID:
            errors.append("SMARTSHEET_SHEET_ID is required when sheet sync is enabled")

    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    logger.info("Configuration validation successful")
