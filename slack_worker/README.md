# Slack Worker Service

The Slack Worker is a scheduled task manager for the OCP Sustaining Bot. It handles batch jobs that need to run on a schedule, such as ROTA QE releases for reminders and notifications.

## Features

-  **Scheduled Jobs**: Uses APScheduler for reliable job scheduling
-  **ROTA Reminders**: Automated release notifications and DM reminders
-  **Horizontal Scaling**: File-based locking prevents duplicate execution
-  **Extensible**: Easy to add new scheduled jobs

## Architecture


## Project Structure

```
slack_worker/
├── slack_worker_main.py       # Main entry point with APScheduler
├── jobs/
│   ├── base_job.py            # Abstract base class for jobs
│   └── rota_reminder_job.py   # ROTA reminder implementation
├── utils/
│   └── lock_manager.py        # Distributed locking mechanism
├── gsheet/
│   └── gsheet.py              # Google Sheets integration (shared)
├── tests/
│   ├── conftest.py            # Test configuration
│   ├── test_lock_manager.py  # Lock manager tests
│   └── test_rota_reminder_job.py  # Job tests
├── Dockerfile                 # Container image definition
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project configuration
├── README.md                 # Full documentation
├── INTEGRATION.md            # Integration with main bot

```


### Design Principles

1. **Independent Service**: Runs as a separate container/pod from the main bot
2. **Modular Jobs**: Each job is independently defined and schedulable
3. **Distributed Coordination**: Uses file locks for multi-instance deployments
4. **Shared Configuration**: Uses same config system as main bot


## ROTA Reminder Schedule

The ROTA reminder job runs on the following schedule:

| Day | Time | Action |
|-----|------|--------|
| **Monday** | 9:00 AM | Post week's releases to group + DM current week participants |
| **Thursday** | 9:00 AM | Post week's releases to group |
| **Friday** | 4:00 PM | DM next week's participants |


### Running Locally

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Run the worker**:
   ```bash
   python slack_worker_main.py
   ```

### Running Tests

```bash
# Run all tests
pytest slack_worker/tests/

# Run with coverage
pytest --cov=slack_worker slack_worker/tests/

# Run specific test
pytest slack_worker/tests/test_rota_reminder_job.py -v
```


### FileLock , How It Works

1. **File-based Locks**: Each job execution attempts to acquire a file lock
2. **Shared Storage**: Lock files are stored on a shared PVC
3. **Timeout Handling**: If lock can't be acquired, job skips (already running)
4. **Automatic Cleanup**: Locks are released after job completes

### Configuration

```python
# In slack_worker_main.py
self.lock_manager = LockManager(lock_dir="/app/locks")

# In job execution
with self.lock_manager.acquire_lock(job_id, timeout=5):
    # Execute job
    pass
```


### Jobs Not Executing

1. Check logs for errors
2. Verify environment variables are set
3. Ensure timezone is correct
4. Check lock directory is accessible


### Slack API Errors

1. Verify bot token is valid
2. Check bot has required permissions
3. Ensure channel IDs are correct

## License

Same as parent project.

## Support

For issues or questions, contact the OCP Sustaining team.

