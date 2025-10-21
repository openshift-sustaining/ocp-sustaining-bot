# Slack Worker Architecture

## Overview

The Slack Worker is a scheduled task service designed to run batch jobs for the OCP Sustaining Bot. It's built with horizontal scalability, reliability, and extensibility as core principles.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Slack API                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ HTTP/WebSocket
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    Slack Worker Pods (Scaled)                    │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Pod 1     │  │   Pod 2     │  │   Pod 3     │             │
│  │             │  │             │  │             │             │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │             │
│  │ │APSchedu-│ │  │ │APSchedu-│ │  │ │APSchedu-│ │             │
│  │ │  ler    │ │  │ │  ler    │ │  │ │  ler    │ │             │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │             │
│  │      │      │  │      │      │  │      │      │             │
│  │ ┌────▼────┐ │  │ ┌────▼────┐ │  │ ┌────▼────┐ │             │
│  │ │  Jobs   │ │  │ │  Jobs   │ │  │ │  Jobs   │ │             │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │             │
│  │      │      │  │      │      │  │      │      │             │
│  │ ┌────▼────┐ │  │ ┌────▼────┐ │  │ ┌────▼────┐ │             │
│  │ │  Lock   │ │  │ │  Lock   │  │  │ │  Lock   │ │             │
│  │ │ Manager │ │  │ │ Manager │ │  │ │ Manager │ │             │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │             │
│  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘             │
│         │                │                │                      │
│         └────────────────┴────────────────┘                      │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                           │ File System
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│              Shared Persistent Volume (PVC)                       │
│                      Lock Files                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ job_1.lock   │ │ job_2.lock   │ │ job_3.lock   │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                      External Services                             │
│                                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Slack     │  │   Google    │  │   Config    │              │
│  │    API      │  │   Sheets    │  │   (Vault)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└───────────────────────────────────────────────────────────────────┘
```



### 1. Scheduler (APScheduler)

**Purpose**: Manages job scheduling and execution timing

**Key Features**:
- Cron-based scheduling
- Timezone support
- Job state management
- Event listeners for monitoring

**Implementation**:
```python
self.scheduler = BlockingScheduler(timezone="UTC")
self.scheduler.add_job(
    func=job.execute,
    trigger=CronTrigger(day_of_week='mon', hour=9),
    id='unique_job_id'
)
```

### 2. Job System

**Purpose**: Extensible framework for defining scheduled tasks

**Base Job Class**:
- Abstract interface for all jobs
- Common Slack posting utilities
- Logging and error handling
- Lock integration

**Job Lifecycle**:
1. Scheduler triggers job at scheduled time
2. Job attempts to acquire lock
3. If lock acquired, job executes
4. Lock released, results logged
5. If lock timeout, job skips (already running)

**Current Jobs**:
- `RotaReminderJob`: ROTA notifications and reminders

### 3. Lock Manager

**Purpose**: Prevents duplicate execution in scaled environments

**How It Works**:
```python
with lock_manager.acquire_lock(job_id, timeout=5):
    # Execute job
    # Only one pod will succeed in acquiring the lock
    pass
```

**Lock Storage**:
- File-based locks on shared PVC
- ReadWriteMany access mode required
- Automatic cleanup after execution
- Timeout handling for stuck locks

**Guarantees**:
- Only one instance executes at a time
- No duplicate notifications
- Safe horizontal scaling

### 4. Integration Layer

**Slack Integration**:
- Uses Slack Bolt SDK
- Supports both channel and DM posting
- Error handling and retry logic

**Google Sheets Integration**:
- Reuses existing GSheet class
- Reads ROTA assignments
- Updates history sheet
- Service account authentication


### Why File Locks?

**Alternatives Considered**:

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **File Locks** | Simple, no dependencies, works in K8s | Requires shared storage | ✅ **Chosen** |
| Database Locks | Centralized, robust | Adds dependency, complexity | ❌ Overkill |
| Leader Election | Kubernetes-native | Complex, requires RBAC | ❌ Too complex |
| Single Pod | Simplest | No HA, single point of failure | ❌ Not scalable |

**File locks** provide the best balance of simplicity, reliability, and horizontal scalability.



### ROTA Reminder Flow

```
┌──────────┐
│ Monday   │
│ 09:00 AM │
└────┬─────┘
     │
     ▼
┌─────────────────┐
│ APScheduler     │
│ Triggers Job    │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Lock Manager    │
│ Acquire Lock    │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ GSheet API      │
│ Fetch ROTA Data │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Format Messages │
│ (Summary + DMs) │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Slack API       │
│ Post Messages   │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Update History  │
│ Sheet (Optional)│
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Release Lock    │
│ Log Success     │
└─────────────────┘
```



### Error Recovery Strategy

| Error Type | Strategy | Example |
|------------|----------|---------|
| **Transient** | Retry with backoff | Slack API rate limit |
| **Permanent** | Log and skip | Invalid configuration |
| **Critical** | Alert and fail | GSheet not initialized |

### Failure Scenarios

**Slack API Failure**:
```python
try:
    self.post_to_slack(channel, message)
except SlackApiError as e:
    logger.error(f"Slack API error: {e}")
    # Don't retry - job will run next scheduled time
```

**GSheet Failure**:
```python
if not gsheet:
    logger.error("GSheet not initialized")
    return  # Skip this execution
```

**Lock Timeout**:
```python
try:
    with lock_manager.acquire_lock(job_id, timeout=5):
        execute_job()
except Timeout:
    logger.warning("Job already running on another pod")
    # This is expected in scaled environments
```


### Adding New Jobs

**1. Create Job Class**:
```python
# slack_worker/jobs/my_new_job.py
from slack_worker.jobs.base_job import BaseJob

class MyNewJob(BaseJob):
    def execute(self):
        # Job logic here
        self.post_to_slack(channel, message)
```

**2. Register in Main**:
```python
# slack_worker_main.py
my_job = MyNewJob(self.slack_app, self.lock_manager)
self.scheduler.add_job(
    func=my_job.execute,
    trigger=CronTrigger(day='1', hour=9),  # Monthly
    id='my_new_job'
)
```

**3. Add Tests**:
```python
# slack_worker/tests/test_my_new_job.py
def test_my_new_job_execution():
    job = MyNewJob(mock_slack_app, None)
    job.execute()
    assert mock_slack_app.client.chat_postMessage.called
```

### Job Requirements

All jobs should:
- ✅ Inherit from `BaseJob`
- ✅ Implement `execute()` method
- ✅ Use lock manager for distributed coordination
- ✅ Handle errors gracefully
- ✅ Log important events
- ✅ Have unit tests



## References

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Slack Bolt SDK](https://slack.dev/bolt-python/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [12-Factor App Methodology](https://12factor.net/)

