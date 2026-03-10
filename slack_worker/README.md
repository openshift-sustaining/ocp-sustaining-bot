# Slack Worker Service

Scheduled job service for ROTA (Release Operations Tracking and Automation) notifications and release synchronization.

## Overview

The Slack Worker runs two main jobs on a schedule:

1. **ROTA Notifications** (`jobs/rota_notifications.py`)
   - Sends release reminders to Slack
   - Schedule: Monday 9 AM (group + DM), Thursday 9 AM (group), Friday 5 PM (DM)
   - Reads from Google Sheets and posts to Slack channels and user DMs

2. **Release Sync** (`jobs/sync_releases.py`)
   - Syncs OCP release data from Smartsheet to Google Sheets
   - Schedule: Daily 8 AM UTC
   - Uses SDK functions for fetch, parse, and write operations

## Architecture

```
Smartsheet (API)
    ↓ [sync_releases.py - 8 AM]
Google Sheets (ROTA - Assignments worksheet)
    ↓ [rota_notifications.py - 9 AM / 5 PM]
Slack (channels + DMs)
```

## Key Components

- **`config.py`** - Configuration management (env variables, scheduling)
- **`slack_client.py`** - Slack API wrapper (messages, DMs)
- **`scheduler.py`** - APScheduler job scheduler
- **`main.py`** - Entry point that initializes and starts the scheduler
- **`jobs/`** - Scheduled job implementations
  - `rota_notifications.py` - ROTA notification logic
  - `sync_releases.py` - Release sync wrapper

## Dependencies

- `slack-sdk>=3.35.0` - Slack API client (WebClient, error handling)
- `gspread==6.2.1` - Google Sheets API
- `apscheduler==3.10.4` - Job scheduling
- `python-dotenv==1.1.0` - Environment variables

## Job Schedules (Cron format)

```bash
SCHEDULE_ROTA_NOTIFICATIONS=0 9 * * MON,THU   
# Monday & Thursday 9 AM
SCHEDULE_ROTA_SHEET_SYNC=0 8 * * MON,THU             
# Monday & Thursday  8 AM
```

### Job Control

Enable/disable jobs by setting schedule (empty string = disabled):

```bash
SCHEDULE_ROTA_NOTIFICATIONS=0 9 * * MON   # Enabled
SCHEDULE_ROTA_NOTIFICATIONS=               # Disabled
```

## Environment Variables

- `SLACK_BOT_TOKEN` - Slack bot API token
- `ROTA_GROUP_CHANNEL` - Slack channel for group reminders
- `ROTA_USERS` - JSON mapping of user names to Slack user IDs
- `ROTA_SERVICE_ACCOUNT` - Google service account JSON (with quotes stripped)
- `SMARTSHEET_ACCESS_TOKEN` - Smartsheet API token
- `SMARTSHEET_SHEET_*_ID` - Smartsheet IDs for OCP versions
- `SCHEDULE_ROTA_SHEET_SYNC` - Cron expression for sync job (e.g., `0 8 * * *`)

## Running

```bash
# With Docker
docker run --env-file .env slack-worker-scheduler:latest

# Locally (requires Python 3.12+)
python slack_worker/main.py
```

## Testing

```bash
# Run tests
pytest tests/

# Test individual components
python -m pytest tests/test_handlers.py -v
```
