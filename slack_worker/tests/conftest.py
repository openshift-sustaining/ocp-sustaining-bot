import json
import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_slack_worker_environment():
    """Setup required environment variables for slack_worker tests"""
    # Core Slack configuration (required)
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token-12345"

    # Rota management (required)
    os.environ["ROTA_USERS"] = "user1,user2,user3"
    os.environ["ROTA_ADMINS"] = "admin1,admin2"
    os.environ["ROTA_SERVICE_ACCOUNT"] = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key-id",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS8JJcds3xfn/J7WdhPsHmN4i6QQZH7dKZGhYgCRKt/+p\nWVPPsLdVKXvSahdvE4kh7vbKgX5vTi9EF2n5qQIDAQABAoIBAEgxBXBkIVa0Hx3Z\nI7GWA7AqD8v3CyKBvVgGlTGQ5OJaQlvB5vKDl9qYsKBvR7mXAhDl8R6bEkS1K3fS\n-----END RSA PRIVATE KEY-----",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )

    # File locking configuration (required)
    os.environ["LOCK_DIR"] = "/tmp/test_locks"
    os.environ["LOCK_TIMEOUT"] = "10"

    # Time zone (required)
    os.environ["TIMEZONE"] = "UTC"
