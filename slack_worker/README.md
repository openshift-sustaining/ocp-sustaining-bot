# Slack Worker Service

The Slack Worker is a scheduled task manager for the OCP Sustaining Bot. It handles batch jobs that need to run on a schedule, such as ROTA reminders and notifications.

## Features

- 🔄 **Scheduled Jobs**: Uses APScheduler for reliable job scheduling
- 📊 **ROTA Reminders**: Automated release notifications and DM reminders
- 🔒 **Horizontal Scaling**: File-based locking prevents duplicate execution
- 📝 **History Tracking**: Updates intermediary Google Sheets for reference
- 🧩 **Extensible**: Easy to add new scheduled jobs

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
├── k8s/
│   └── deployment.yaml        # K8s/OCP deployment manifests
├── Dockerfile                 # Container image definition
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project configuration
├── docker-compose.yml        # Local testing setup
├── .gitlab-ci.yml            # CI/CD pipeline
├── README.md                 # Full documentation
├── QUICKSTART.md             # Quick setup guide
├── DEPLOYMENT.md             # Deployment guide
├── ARCHITECTURE.md           # System design
├── INTEGRATION.md            # Integration with main bot
└── SUMMARY.md                # This file
```


### Design Principles

1. **Independent Service**: Runs as a separate container/pod from the main bot
2. **Modular Jobs**: Each job is independently defined and schedulable
3. **Distributed Coordination**: Uses file locks for multi-instance deployments
4. **Shared Configuration**: Uses same config system as main bot

### Components

```
slack_worker/
├── slack_worker_main.py      # Main entry point
├── jobs/                      # Job definitions
│   ├── base_job.py           # Abstract base class
│   └── rota_reminder_job.py  # ROTA reminder implementation
├── utils/                     # Utilities
│   └── lock_manager.py       # Distributed locking
├── gsheet/                    # Google Sheets integration
│   └── gsheet.py
├── tests/                     # Unit tests
├── Dockerfile                 # Container image
└── requirements.txt           # Python dependencies
```

## ROTA Reminder Schedule

The ROTA reminder job runs on the following schedule:

| Day | Time | Action |
|-----|------|--------|
| **Monday** | 9:00 AM | Post week's releases to group + DM current week participants |
| **Thursday** | 9:00 AM | Post week's releases to group |
| **Friday** | 4:00 PM | DM next week's participants |

## Configuration

### Environment Variables

Key environment variables:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ROTA_GROUP_CHANNEL=C123456789

# Team Configuration
ROTA_TEAM_LEADS=Lead1,Lead2,Lead3
ROTA_TEAM_MEMBERS=Member1,Member2,Member3

# Scheduling
TIMEZONE=America/New_York

# Locking (for horizontal scaling)
LOCK_DIR=/app/locks  # Use shared PVC in K8s/OCP
```

See `.env.example` for full configuration options.

### Google Sheets

The service uses the same Google Sheets integration as the main bot:

- **ROTA Sheet**: Main sheet with release assignments
- **History Sheet**: Optional intermediary sheet for tracking

Team members and leads should be configured via environment variables rather than hardcoded.

## Development

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

### Adding a New Job

1. **Create job class** in `jobs/`:
   ```python
   from slack_worker.jobs.base_job import BaseJob
   
   class MyNewJob(BaseJob):
       def execute(self):
           # Your job logic here
           pass
   ```

2. **Register in `slack_worker_main.py`**:
   ```python
   def register_jobs(self):
       my_job = MyNewJob(self.slack_app, self.lock_manager)
       self.scheduler.add_job(
           func=my_job.execute,
           trigger=CronTrigger(day_of_week='mon', hour=10),
           id='my_new_job',
           name='My New Job'
       )
   ```

3. **Add tests** in `tests/`:
   ```python
   class TestMyNewJob:
       def test_execution(self, mock_slack_app):
           job = MyNewJob(mock_slack_app, None)
           job.execute()
           # Assert expected behavior
   ```

## Deployment

### Docker

Build the image:
```bash
docker build -f slack_worker/Dockerfile -t slack-worker:latest .
```

Run the container:
```bash
docker run -d \
  --name slack-worker \
  -e SLACK_BOT_TOKEN=... \
  -e SLACK_APP_TOKEN=... \
  -v /path/to/locks:/app/locks \
  slack-worker:latest
```

### Kubernetes/OpenShift

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: slack-worker
spec:
  replicas: 2  # Can scale horizontally
  selector:
    matchLabels:
      app: slack-worker
  template:
    metadata:
      labels:
        app: slack-worker
    spec:
      containers:
      - name: slack-worker
        image: slack-worker:latest
        env:
        - name: SLACK_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: slack-secrets
              key: bot-token
        - name: LOCK_DIR
          value: /app/locks
        volumeMounts:
        - name: lock-storage
          mountPath: /app/locks
      volumes:
      - name: lock-storage
        persistentVolumeClaim:
          claimName: slack-worker-locks
```

**Important**: When scaling horizontally in K8s/OCP:
- Use a **shared PVC** for the lock directory
- File locks prevent duplicate job execution
- All pods can scale independently

### CI/CD Pipeline

The worker should have its own build pipeline:

1. **Pre-build**: Run tests and linters
2. **Build**: Build Docker image
3. **Deploy**: Deploy to K8s/OCP

Example GitLab CI:
```yaml
slack-worker-test:
  script:
    - cd slack_worker
    - pip install -r requirements.txt
    - pytest tests/

slack-worker-build:
  script:
    - docker build -f slack_worker/Dockerfile -t slack-worker:$CI_COMMIT_SHA .
    - docker push slack-worker:$CI_COMMIT_SHA
```

## Horizontal Scaling

The service is designed to scale horizontally:

### How It Works

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

### Best Practices

- **Use shared PVC** in K8s/OCP for lock directory
- **Set reasonable timeouts** for lock acquisition
- **Monitor lock files** to ensure they're being cleaned up
- **Test scaling** with multiple replicas


### Jobs Not Executing

1. Check logs for errors
2. Verify environment variables are set
3. Ensure timezone is correct
4. Check lock directory is accessible

### Duplicate Execution

1. Verify shared PVC is mounted
2. Check lock directory permissions
3. Ensure lock timeout is reasonable

### Slack API Errors

1. Verify bot token is valid
2. Check bot has required permissions
3. Ensure channel IDs are correct

## License

Same as parent project.

## Support

For issues or questions, contact the OCP Sustaining team.

