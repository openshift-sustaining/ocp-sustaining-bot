# Integration with Main Bot

This document explains how the Slack Worker integrates with the main bot and shared components.

## Overview

The Slack Worker is a **separate service** but shares code and configuration with the main bot:

```
ocp-sustaining-bot/
├── config.py              # Shared configuration
├── slack_main.py          # Main bot (interactive)
├── slack_handlers/        # Main bot handlers
│   └── handlers.py        # Contains ROTA command handlers
└── slack_worker/          # Worker service (scheduled)
    ├── slack_worker_main.py
    ├── jobs/
    └── gsheet/
        └── gsheet.py      # Shared GSheet integration
```

## Shared Components

### 1. Configuration (config.py)

Both services use the same configuration system:

```python
# config.py (root)
from dynaconf import Dynaconf

config = Dynaconf(
    load_dotenv=True,
    environment=False,
    vault_enabled=vault_enabled,
)
```

**Shared Configuration**:
- `SLACK_BOT_TOKEN`: Used by both for API access
- `SLACK_APP_TOKEN`: Used by main bot for Socket Mode
- `ROTA_USERS`: User ID mapping (used by both)
- `ROTA_ADMINS`: Admin users (main bot only)
- Google Sheets credentials (both)

**Worker-Specific Configuration**:
- `ROTA_GROUP_CHANNEL`: Channel for notifications
- `ROTA_TEAM_LEADS`: Team leads list
- `ROTA_TEAM_MEMBERS`: Team members list
- `LOCK_DIR`: Lock file directory
- `TIMEZONE`: Scheduling timezone

### 2. Google Sheets Integration

The worker **reuses** the GSheet class from `slack_worker/gsheet/gsheet.py`:

```python
# Originally in slack_handlers/handlers.py, now moved to:
# slack_worker/gsheet/gsheet.py

from slack_worker.gsheet.gsheet import gsheet

# Both services can use:
data = gsheet.fetch_data_by_time("This Week")
```

**Why Share?**
- Avoid code duplication
- Consistent data access
- Single point of maintenance


## Integration Points

### 1. Command vs Scheduled Execution

**Main Bot** (User-triggered):
```
User: @bot rota --check --time="This Week"
Bot: *Release: 4.15.1*
     *Patch Manager: @john*
     *QE: @jane, @bob*
```

**Worker** (Automated):
```
[Monday 9:00 AM - Automatic]
Bot → Group Channel:
📢 *This Week's Releases:*

*Release: 4.15.1*
*Dates: 2024-01-15 → 2024-01-19*
*Patch Manager: @john*
*QE: @jane, @bob*

Bot → DMs:
👋 Hi @john! Reminder: You're assigned to *4.15.1* (This Week).
```

### 2. Data Flow

Both services read from the same Google Sheet:

```
Google Sheets (ROTA)
        ↓
    ┌───────────────┐
    │  GSheet API   │
    └───────┬───────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
Main Bot      Slack Worker
(On-demand)   (Scheduled)
    │               │
    └───────┬───────┘
            ▼
      Slack API
```

## Communication Between Services

**No Direct Communication**:
- Main bot and worker are **independent**
- No API calls between them
- Communication only through:
  - Shared Google Sheets (data)
  - Shared configuration (settings)
  - Slack API (both post messages)

**Why Independent?**
- ✅ Simple architecture
- ✅ No coupling
- ✅ Easy to scale separately
- ✅ Failures isolated
- ✅ Can deploy separately

