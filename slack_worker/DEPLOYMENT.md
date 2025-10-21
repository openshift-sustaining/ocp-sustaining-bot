# Slack Worker Deployment Guide

This guide covers deploying the Slack Worker service to various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes/OpenShift Deployment](#kubernetesopenshift-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- Python 3.11+
- Docker (for containerized deployment)
- Kubernetes/OpenShift cluster (for production)
- Slack Bot Token and App Token
- Google Sheets API credentials
- Shared storage (PVC) for horizontal scaling

### Optional

- GitLab Runner (for CI/CD)
- Prometheus (for metrics)
- Grafana (for dashboards)

## Local Development

### 1. Setup Environment

```bash
# Clone repository
cd ocp-sustaining-bot/slack_worker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
ROTA_GROUP_CHANNEL=C123456789
ROTA_TEAM_LEADS=Lead1,Lead2
ROTA_TEAM_MEMBERS=Member1,Member2,Member3
TIMEZONE=America/New_York
```

### 3. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 4. Run Locally

```bash
python slack_worker_main.py
```

The service will start and display scheduled jobs:
```
==============================================================
Starting Slack Worker Service
Timezone: America/New_York
Lock Directory: /tmp/slack_worker_locks
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

## Docker Deployment

### 1. Build Image

From the **repository root**:

```bash
docker build -f slack_worker/Dockerfile -t slack-worker:latest .
```

### 2. Run Container

Single instance:

```bash
docker run -d \
  --name slack-worker \
  -e SLACK_BOT_TOKEN=xoxb-... \
  -e SLACK_APP_TOKEN=xapp-... \
  -e ROTA_GROUP_CHANNEL=C123456789 \
  -e ROTA_TEAM_LEADS=Lead1,Lead2 \
  -e ROTA_TEAM_MEMBERS=Member1,Member2,Member3 \
  -e TIMEZONE=America/New_York \
  -v /tmp/locks:/app/locks \
  slack-worker:latest
```

### 3. Docker Compose

For easier local testing:

```bash
cd slack_worker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Kubernetes/OpenShift Deployment

### 1. Prerequisites

- Access to K8s/OCP cluster
- kubectl/oc CLI configured
- Docker registry access

### 2. Build and Push Image

```bash
# Build
docker build -f slack_worker/Dockerfile -t your-registry/slack-worker:v1.0 .

# Push
docker push your-registry/slack-worker:v1.0
```

### 3. Create Namespace

```bash
kubectl create namespace slack-worker
# Or for OpenShift:
oc new-project slack-worker
```

### 4. Create Secrets

Create `secrets.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: slack-secrets
  namespace: slack-worker
type: Opaque
stringData:
  bot-token: "xoxb-your-bot-token"
  app-token: "xapp-your-app-token"

---
apiVersion: v1
kind: Secret
metadata:
  name: gsheet-secrets
  namespace: slack-worker
type: Opaque
stringData:
  service-account: |
    {
      "type": "service_account",
      "project_id": "your-project",
      ...
    }
```

Apply:
```bash
kubectl apply -f secrets.yaml
```

### 5. Create ConfigMap

```bash
kubectl create configmap slack-worker-config \
  --namespace=slack-worker \
  --from-literal=group-channel=C123456789 \
  --from-literal=team-leads=Lead1,Lead2,Lead3 \
  --from-literal=team-members=Member1,Member2,Member3
```

### 6. Create Persistent Volume Claim

**Critical for horizontal scaling!**

```bash
kubectl apply -f k8s/deployment.yaml
```

This creates:
- PVC with ReadWriteMany access mode
- Deployment with 2 replicas
- ConfigMap and Secrets

### 7. Verify Deployment

```bash
# Check pods
kubectl get pods -n slack-worker

# Check logs
kubectl logs -f deployment/slack-worker -n slack-worker

# Check PVC
kubectl get pvc -n slack-worker
```

### 8. Scale Deployment

```bash
# Scale up
kubectl scale deployment/slack-worker --replicas=3 -n slack-worker

# Scale down
kubectl scale deployment/slack-worker --replicas=1 -n slack-worker
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | Yes | - | Slack bot OAuth token |
| `SLACK_APP_TOKEN` | Yes | - | Slack app-level token |
| `ROTA_GROUP_CHANNEL` | Yes | - | Channel ID for group notifications |
| `ROTA_TEAM_LEADS` | No | [] | Comma-separated list of team leads |
| `ROTA_TEAM_MEMBERS` | No | [] | Comma-separated list of team members |
| `ROTA_SERVICE_ACCOUNT` | Yes | - | Google Sheets service account JSON |
| `ROTA_SHEET` | No | ROTA | Google Sheet name |
| `ASSIGNMENT_WSHEET` | No | Assignments | Worksheet name |
| `TIMEZONE` | No | UTC | Timezone for scheduling |
| `LOCK_DIR` | No | /tmp/slack_worker_locks | Directory for lock files |
| `LOG_LEVEL` | No | INFO | Logging level |

### Job Schedules

Modify schedules in `slack_worker_main.py`:

```python
# Monday at 9:00 AM
self.scheduler.add_job(
    func=rota_job.execute,
    trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
    ...
)
```

Cron expression examples:
- `day_of_week='mon,wed,fri'` - Monday, Wednesday, Friday
- `hour=9, minute=30` - 9:30 AM
- `day='1'` - First day of month
- `day_of_week='0-4', hour='9-17'` - Weekdays, 9 AM to 5 PM

## Monitoring

### Logging

Logs are written to stdout/stderr and captured by container runtime:

```bash
# Kubernetes
kubectl logs -f deployment/slack-worker -n slack-worker

# Docker
docker logs -f slack-worker

# Follow specific pod
kubectl logs -f slack-worker-abc123-xyz -n slack-worker
```

### Health Checks

The deployment includes liveness and readiness probes:

```yaml
livenessProbe:
  exec:
    command:
    - /bin/sh
    - -c
    - pgrep -f slack_worker_main.py
  initialDelaySeconds: 30
  periodSeconds: 30
```

Check health:
```bash
kubectl describe pod slack-worker-xxx -n slack-worker
```

### Metrics (Future Enhancement)

Planned Prometheus metrics:
- `slack_worker_jobs_total` - Total jobs executed
- `slack_worker_jobs_failed` - Failed jobs count
- `slack_worker_lock_acquisitions` - Lock acquisition metrics
- `slack_worker_execution_duration` - Job execution time

## Troubleshooting

### Pods Not Starting

**Symptoms**: Pods in `CrashLoopBackOff` or `Error` state

**Solutions**:

1. Check logs:
   ```bash
   kubectl logs slack-worker-xxx -n slack-worker
   ```

2. Verify secrets exist:
   ```bash
   kubectl get secrets -n slack-worker
   ```

3. Check environment variables:
   ```bash
   kubectl exec slack-worker-xxx -n slack-worker -- env | grep SLACK
   ```

### Jobs Not Executing

**Symptoms**: No messages posted to Slack

**Solutions**:

1. Verify timezone configuration:
   ```bash
   kubectl exec slack-worker-xxx -n slack-worker -- date
   ```

2. Check job schedule:
   ```bash
   kubectl logs slack-worker-xxx -n slack-worker | grep "Next run"
   ```

3. Verify Slack permissions:
   - Bot needs `chat:write` scope
   - Bot needs `im:write` for DMs
   - Bot must be added to target channel

### Duplicate Job Execution

**Symptoms**: Same job runs multiple times

**Solutions**:

1. Verify PVC is ReadWriteMany:
   ```bash
   kubectl get pvc slack-worker-locks -n slack-worker -o yaml
   ```

2. Check lock directory is shared:
   ```bash
   kubectl exec slack-worker-xxx -n slack-worker -- ls -la /app/locks
   ```

3. Verify lock files are created:
   ```bash
   kubectl exec slack-worker-xxx -n slack-worker -- ls /app/locks/
   ```

### Google Sheets API Errors

**Symptoms**: "GSheet not initialized" errors

**Solutions**:

1. Verify service account JSON is valid:
   ```bash
   kubectl get secret gsheet-secrets -n slack-worker -o yaml
   ```

2. Check Google Sheet permissions:
   - Service account email must have edit access
   - Sheet must exist
   - Worksheet names must match

3. Test API access:
   ```python
   # In a debug pod
   import gspread
   gc = gspread.service_account_from_dict(json_data)
   sheet = gc.open("ROTA")
   ```

### Lock File Issues

**Symptoms**: Timeouts acquiring locks, stale locks

**Solutions**:

1. Clean up stale locks:
   ```bash
   kubectl exec slack-worker-xxx -n slack-worker -- rm /app/locks/*.lock
   ```

2. Check lock directory permissions:
   ```bash
   kubectl exec slack-worker-xxx -n slack-worker -- ls -ld /app/locks
   # Should be drwxrwxrwx
   ```

3. Verify PVC is healthy:
   ```bash
   kubectl describe pvc slack-worker-locks -n slack-worker
   ```

### High CPU/Memory Usage

**Symptoms**: Pods throttled or OOMKilled

**Solutions**:

1. Increase resource limits:
   ```yaml
   resources:
     limits:
       cpu: 1000m
       memory: 1Gi
   ```

2. Check for memory leaks in logs

3. Optimize job execution

## CI/CD Integration

### GitLab CI

The `.gitlab-ci.yml` file includes:
- Automated testing on commits
- Docker image building
- Deployment to dev/prod environments

Trigger pipeline:
```bash
git push origin main
```

Manual production deployment:
```bash
# In GitLab UI: Pipelines > Run Pipeline > deploy:slack-worker-prod
```

### Jenkins (Alternative)

Example Jenkinsfile:

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'cd slack_worker && pytest tests/'
            }
        }
        stage('Build') {
            steps {
                sh 'docker build -f slack_worker/Dockerfile -t slack-worker:${BUILD_NUMBER} .'
            }
        }
        stage('Deploy') {
            steps {
                sh 'kubectl set image deployment/slack-worker slack-worker=slack-worker:${BUILD_NUMBER}'
            }
        }
    }
}
```

## Backup and Recovery

### Backup Lock Files

```bash
kubectl exec slack-worker-xxx -n slack-worker -- tar czf /tmp/locks-backup.tar.gz /app/locks
kubectl cp slack-worker-xxx:/tmp/locks-backup.tar.gz ./locks-backup.tar.gz -n slack-worker
```

### Restore

```bash
kubectl cp ./locks-backup.tar.gz slack-worker-xxx:/tmp/locks-backup.tar.gz -n slack-worker
kubectl exec slack-worker-xxx -n slack-worker -- tar xzf /tmp/locks-backup.tar.gz -C /
```

## Rolling Updates

```bash
# Update image
kubectl set image deployment/slack-worker \
  slack-worker=your-registry/slack-worker:v2.0 \
  -n slack-worker

# Monitor rollout
kubectl rollout status deployment/slack-worker -n slack-worker

# Rollback if needed
kubectl rollout undo deployment/slack-worker -n slack-worker
```

## Security Best Practices

1. **Secrets Management**
   - Use Kubernetes Secrets or Vault
   - Never commit secrets to git
   - Rotate tokens regularly

2. **RBAC**
   - Create service account with minimal permissions
   - Use NetworkPolicies to restrict traffic

3. **Image Security**
   - Scan images for vulnerabilities
   - Use official base images
   - Keep dependencies updated

4. **Audit Logging**
   - Enable audit logs for compliance
   - Monitor API access patterns
   - Alert on suspicious activity

## Support

For issues or questions:
- Check logs first
- Review troubleshooting section
- Contact OCP Sustaining team
- Open GitHub issue

## Additional Resources

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Slack Bolt Python](https://slack.dev/bolt-python/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [OpenShift Documentation](https://docs.openshift.com/)

