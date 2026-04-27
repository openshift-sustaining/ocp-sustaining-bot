import json
import os

# Set env vars at module level so they're available during collection,
# before test files import slack_worker.config (which validates at import time).

# slack_worker/config.py required keys
os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token-12345"
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
os.environ["LOCK_DIR"] = "/tmp/test_locks"
os.environ["LOCK_TIMEOUT"] = "10"
os.environ["TIMEZONE"] = "UTC"

# Root config.py required keys (needed because slack_worker.jobs transitively
# imports sdk.gsheet.gsheet which imports the root config module).
os.environ["GOOGLE_CLOUD_CREDS"] = json.dumps(
    {"type": "service_account", "project_id": "test"}
)
os.environ["SLACK_APP_TOKEN"] = "xapp-test-token"
os.environ["AWS_ACCESS_KEY_ID"] = "AKIAIOSFODNN7EXAMPLE"
os.environ["AWS_SECRET_ACCESS_KEY"] = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["OS_AUTH_URL"] = "https://auth.example.com/v3"
os.environ["OS_PROJECT_ID"] = "test-project-id"
os.environ["OS_INTERFACE"] = "public"
os.environ["OS_ID_API_VERSION"] = "3"
os.environ["OS_REGION_NAME"] = "regionOne"
os.environ["OS_APP_CRED_ID"] = "test-cred-id"
os.environ["OS_APP_CRED_SECRET"] = "test-cred-secret"
os.environ["OS_AUTH_TYPE"] = "v3applicationcredential"
os.environ["ALLOW_ALL_WORKSPACE_USERS"] = "false"
os.environ["ALLOWED_SLACK_USERS"] = "false"
os.environ["AWS_AMI_MAP"] = '{"linux": "ami-dummy"}'
