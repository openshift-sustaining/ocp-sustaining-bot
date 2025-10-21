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

### 3. ROTA Logic

**Before (All in Main Bot)**:
```
slack_main.py → slack_handlers/handlers.py
                └── handle_rota()
                    ├── Interactive commands
                    └── Reminder logic (manual)
```

**After (Separated)**:
```
Main Bot (Interactive):
slack_main.py → slack_handlers/handlers.py
                └── handle_rota()
                    ├── rota --add
                    ├── rota --check
                    └── rota --replace

Worker (Scheduled):
slack_worker_main.py → jobs/rota_reminder_job.py
                       └── execute()
                           ├── Post summaries
                           └── Send DM reminders
```

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

### 3. User Mapping

Both use `config.ROTA_USERS` for name-to-ID mapping:

```python
# config.py
ROTA_USERS = {
    "John Doe": "U123456",
    "Jane Smith": "U234567",
    "Bob Wilson": "U345678"
}

# Used by both:
slack_id = config.ROTA_USERS.get(name)
mention = f"<@{slack_id}>"
```

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────┐
│          Developer Machine              │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  slack_main  │  │ slack_worker │   │
│  │    .py       │  │   _main.py   │   │
│  └──────┬───────┘  └──────┬───────┘   │
│         │                  │            │
│         └──────────┬───────┘            │
│                    │                    │
│         ┌──────────▼────────┐           │
│         │    config.py      │           │
│         └───────────────────┘           │
└─────────────────────────────────────────┘
```

### Production Environment

```
┌─────────────────────────────────────────┐
│          Kubernetes Cluster             │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │    Main Bot Deployment           │  │
│  │  ┌────────┐  ┌────────┐         │  │
│  │  │ Pod 1  │  │ Pod 2  │         │  │
│  │  └────────┘  └────────┘         │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Slack Worker Deployment        │  │
│  │  ┌────────┐  ┌────────┐         │  │
│  │  │ Pod 1  │  │ Pod 2  │         │  │
│  │  └───┬────┘  └───┬────┘         │  │
│  │      │           │               │  │
│  │      └─────┬─────┘               │  │
│  │            │                     │  │
│  │      ┌─────▼─────┐               │  │
│  │      │  Shared   │               │  │
│  │      │    PVC    │               │  │
│  │      │  (Locks)  │               │  │
│  │      └───────────┘               │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │        ConfigMap/Secrets         │  │
│  │  - Slack Tokens                  │  │
│  │  - GSheet Credentials            │  │
│  │  - ROTA Configuration            │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
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

## Migration Guide

If you're migrating from Slack Workflows to this bot:

### 1. Update Slack Workflow

**Before**: 3 separate workflows
- Check release (manual)
- Remind on DM (scheduled)
- Remind on group (scheduled)

**After**: 1 command + 3 scheduled jobs
- `@bot rota --check` (interactive)
- Worker handles reminders (automated)

### 2. Migration Steps

```bash
# Step 1: Deploy worker
kubectl apply -f slack_worker/k8s/deployment.yaml

# Step 2: Verify worker is running
kubectl get pods -n slack-worker

# Step 3: Disable old Slack workflows
# (In Slack workflow settings)

# Step 4: Test new system
@bot rota --check --time="This Week"

# Step 5: Wait for scheduled execution
# Monitor logs for Monday 9am execution
kubectl logs -f deployment/slack-worker -n slack-worker
```

### 3. Rollback Plan

If issues occur:

```bash
# Stop worker
kubectl scale deployment/slack-worker --replicas=0 -n slack-worker

# Re-enable Slack workflows
# (In Slack workflow settings)

# Fix issues, then re-enable worker
kubectl scale deployment/slack-worker --replicas=2 -n slack-worker
```

## API Wrapper (Future)

Planned feature: Allow main bot to trigger worker jobs on-demand.

### Future Architecture

```python
# Main bot command
@app.command("/rota-notify-now")
def handle_notify_now(ack, command):
    ack()
    
    # Trigger worker job via API
    response = requests.post(
        "http://slack-worker-api:8080/jobs/rota-reminder/trigger",
        json={"period": "This Week"}
    )
    
    say(f"Notification sent: {response.json()}")
```

```python
# Worker API endpoint
from fastapi import FastAPI

app = FastAPI()

@app.post("/jobs/rota-reminder/trigger")
def trigger_rota_reminder(request: dict):
    period = request.get("period", "This Week")
    rota_job.execute()  # Execute immediately
    return {"status": "success", "period": period}
```

This would enable:
- On-demand job execution
- Manual retry of failed jobs
- Testing in production
- Emergency notifications

## Environment Variables

### Shared Variables

Both services need:
```bash
SLACK_BOT_TOKEN=xoxb-...
ROTA_SERVICE_ACCOUNT={"type":"service_account",...}
ROTA_USERS={"John Doe":"U123456",...}
ROTA_SHEET=ROTA
ASSIGNMENT_WSHEET=Assignments
```

### Main Bot Only

```bash
SLACK_APP_TOKEN=xapp-...  # For Socket Mode
ALLOWED_SLACK_USERS={"user1":"U111",...}
ROTA_ADMINS={"admin1":"U999",...}
```

### Worker Only

```bash
ROTA_GROUP_CHANNEL=C123456789
ROTA_TEAM_LEADS=Lead1,Lead2
ROTA_TEAM_MEMBERS=Member1,Member2
TIMEZONE=America/New_York
LOCK_DIR=/app/locks
```

## Testing Integration

### Test Both Services

```bash
# Terminal 1: Run main bot
python slack_main.py

# Terminal 2: Run worker
cd slack_worker
python slack_worker_main.py

# Terminal 3: Test interaction
# In Slack:
@bot rota --check --time="This Week"

# Verify both work independently
# and access same data
```

### Integration Test Script

```python
# test_integration.py
def test_main_bot_and_worker_use_same_data():
    # Main bot fetches data
    from slack_handlers.handlers import handle_rota
    from slack_worker.gsheet.gsheet import gsheet
    
    # Both should return same data
    data1 = gsheet.fetch_data_by_time("This Week")
    data2 = gsheet.fetch_data_by_time("This Week")
    
    assert data1 == data2
```

## Troubleshooting Integration

### Issue: Different Data in Main Bot vs Worker

**Cause**: Using different service accounts or sheets

**Fix**: Verify both use same config
```bash
# In main bot logs
grep "ROTA_SHEET" logs.txt

# In worker logs
kubectl logs deployment/slack-worker -n slack-worker | grep "ROTA_SHEET"

# Should match!
```

### Issue: User Mentions Not Working

**Cause**: `ROTA_USERS` mapping not configured

**Fix**: Add user mapping to config
```python
# config.py or environment
ROTA_USERS = {
    "John Doe": "U123456",
    "Jane Smith": "U234567"
}
```

### Issue: Worker Can't Import Shared Code

**Cause**: Python path not configured

**Fix**: Ensure parent directory in path
```python
# slack_worker_main.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now can import:
from config import config
```

## Best Practices

### 1. Keep Config in Sync

Use same secrets/config for both:
```yaml
# kubernetes secret (shared by both)
apiVersion: v1
kind: Secret
metadata:
  name: slack-shared-secrets
data:
  slack-bot-token: ...
  gsheet-credentials: ...
```

### 2. Version Together

When updating shared code (config.py, gsheet.py):
- Test both services
- Deploy both together
- Version tag applies to both

### 3. Monitor Both

```bash
# View both logs simultaneously
kubectl logs -f deployment/slack-bot -n production &
kubectl logs -f deployment/slack-worker -n slack-worker &
```

### 4. Document Changes

When changing shared components:
- Update both README files
- Test both services
- Update integration tests
- Document breaking changes

## Summary

- **Main Bot**: Interactive, user-triggered commands
- **Worker**: Scheduled, automated reminders
- **Shared**: Config, GSheet integration, user mappings
- **Independent**: Deployments, scaling, failures
- **Future**: API wrapper for on-demand triggers

Both services work together to provide a complete ROTA management solution!

