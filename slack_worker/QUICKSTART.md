# Slack Worker Quick Start Guide

Get the Slack Worker up and running in under 10 minutes!

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Slack bot with tokens (bot token, app token)
- [ ] Google Sheets API credentials
- [ ] Access to ROTA Google Sheet

## Step-by-Step Setup

### 1. Clone and Navigate (30 seconds)

```bash
cd ocp-sustaining-bot/slack_worker
```

### 2. Install Dependencies (2 minutes)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. Configure Environment (2 minutes)

Create `.env` file:

```bash
cat > .env << 'EOF'
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
ROTA_GROUP_CHANNEL=C123456789

# Team Configuration
ROTA_TEAM_LEADS=Alice,Bob
ROTA_TEAM_MEMBERS=Charlie,Diana,Eve

# Google Sheets
ROTA_SERVICE_ACCOUNT={"type":"service_account","project_id":"your-project",...}
ROTA_SHEET=ROTA
ASSIGNMENT_WSHEET=Assignments

# Scheduling
TIMEZONE=America/New_York
LOG_LEVEL=INFO
EOF
```

**Required Updates**:
1. Replace `SLACK_BOT_TOKEN` with your actual token
2. Replace `SLACK_APP_TOKEN` with your actual token
3. Replace `ROTA_GROUP_CHANNEL` with your channel ID
4. Update team members list
5. Add your Google Sheets service account JSON

### 4. Verify Configuration (30 seconds)

```bash
# Test configuration loading
python -c "from config import config; print('Config OK')"
```

### 5. Run Tests (1 minute)

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_lock_manager.py::TestLockManager::test_acquire_and_release_lock PASSED
tests/test_rota_reminder_job.py::TestRotaReminderJob::test_monday_execution PASSED
...
==================== X passed in X.XXs ====================
```

### 6. Start the Worker (30 seconds)

```bash
python slack_worker_main.py
```

You should see:
```
==============================================================
Starting Slack Worker Service
Timezone: America/New_York
Lock Directory: /tmp/slack_worker_locks
==============================================================
Registered job: ROTA Monday Reminder (Mon 9:00 AM)
Registered job: ROTA Thursday Reminder (Thu 9:00 AM)
Registered job: ROTA Friday Reminder (Fri 4:00 PM)
==============================================================
Scheduled Jobs:
  - ROTA Monday Reminder (ID: rota_monday_reminder)
    Next run: 2024-01-15 09:00:00
  - ROTA Thursday Reminder (ID: rota_thursday_reminder)
    Next run: 2024-01-18 09:00:00
  - ROTA Friday Reminder (ID: rota_friday_reminder)
    Next run: 2024-01-19 16:00:00
==============================================================
```

🎉 **Success!** The worker is now running and will execute jobs at scheduled times.

## Docker Quick Start (Alternative)

### 1. Build Image

```bash
cd ..  # Go to repository root
docker build -f slack_worker/Dockerfile -t slack-worker:latest .
```

### 2. Run Container

```bash
docker run -d \
  --name slack-worker \
  --env-file slack_worker/.env \
  -v $(pwd)/locks:/app/locks \
  slack-worker:latest
```

### 3. View Logs

```bash
docker logs -f slack-worker
```

## Testing the Service

### Manual Test (Immediate Execution)

To test without waiting for scheduled time, modify `slack_worker_main.py` temporarily:

```python
# Add after register_jobs():
logger.info("Running test execution...")
rota_job.execute()
```

Then run:
```bash
python slack_worker_main.py
```

### Verify Slack Messages

1. Check your configured group channel for release summary
2. Check DMs for team members assigned to releases
3. Verify message formatting is correct

### Check Google Sheets

1. Open your ROTA sheet
2. Verify data is being read correctly
3. Check history sheet is updated (if configured)

## Common Issues and Quick Fixes

### Issue: "Module not found" errors

**Fix**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Could not read key from Vault"

**Fix**: Disable Vault if not using it
```bash
echo "VAULT_ENABLED_FOR_DYNACONF=false" >> .env
```

### Issue: "GSheet not initialized"

**Fix**: Verify service account JSON is valid
```bash
# Check JSON syntax
python -c "import json; json.loads(open('.env').read().split('ROTA_SERVICE_ACCOUNT=')[1].split('\n')[0])"
```

### Issue: Slack messages not posting

**Fix**: Verify bot permissions
- Bot needs `chat:write` scope
- Bot needs `im:write` for DMs
- Bot must be invited to target channel

### Issue: Jobs not executing at scheduled time

**Fix**: Check timezone configuration
```bash
echo "TIMEZONE=America/New_York" >> .env
# Or use your local timezone
```

## Next Steps

### 1. Deploy to Production

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Kubernetes/OpenShift deployment
- Docker Compose setup
- CI/CD pipeline configuration

### 2. Add More Jobs

See [README.md](README.md) for:
- Creating new job classes
- Registering jobs with scheduler
- Writing tests for jobs

### 3. Configure Monitoring

See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- Logging configuration
- Health checks
- Metrics (planned)

## Useful Commands

```bash
# Run tests with coverage
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# Check code style
black . --check
flake8 .

# View scheduled jobs (while running)
# (Press Ctrl+C to stop)
python slack_worker_main.py

# Clean up lock files
rm -rf /tmp/slack_worker_locks/*.lock

# View logs in production
kubectl logs -f deployment/slack-worker -n slack-worker
```

## Get Help

- 📖 [README.md](README.md) - Full documentation
- 🏗️ [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- 🚀 [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- 🐛 Issues - Open a GitHub issue
- 💬 Support - Contact OCP Sustaining team

## Checklist for Production

Before deploying to production:

- [ ] All tests pass
- [ ] Secrets configured in Kubernetes
- [ ] PVC created with ReadWriteMany
- [ ] Environment variables set correctly
- [ ] Team members list is up to date
- [ ] Timezone is correct
- [ ] Channel IDs verified
- [ ] Bot permissions confirmed
- [ ] Google Sheets access verified
- [ ] CI/CD pipeline configured
- [ ] Monitoring/logging set up
- [ ] Tested with multiple replicas
- [ ] Rollback plan documented

---

**Ready to deploy?** Follow the [DEPLOYMENT.md](DEPLOYMENT.md) guide!

**Need help?** Check [README.md](README.md) for detailed documentation.

**Understanding the system?** Read [ARCHITECTURE.md](ARCHITECTURE.md) for design details.

