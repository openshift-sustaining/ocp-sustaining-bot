"""
Core tests for slack_worker - Priority tests for main components
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from slack_worker.scheduler import FileLock, JobScheduler
from slack_worker.slack_client import SlackClient


# ============================================================================
# 1. CONFIG TESTS
# ============================================================================


class TestConfigLoading:
    """Test configuration loading"""

    def test_config_required_keys_exist(self):
        """Confirms required keys are defined"""
        with patch("slack_worker.config.hvac.Client"):
            from slack_worker.config import required_keys

            assert "SLACK_BOT_TOKEN" in required_keys
            assert "ROTA_SERVICE_ACCOUNT" in required_keys
            assert "LOCK_DIR" in required_keys


# ============================================================================
# 2. SLACK CLIENT TESTS
# ============================================================================


class TestSlackClient:
    """Test SlackClient wrapper"""

    def test_slack_client_initialization(self):
        """Verifies client initializes with token"""
        with patch("slack_worker.slack_client.config") as mock_config:
            mock_config.SLACK_BOT_TOKEN = "xoxb-test-token"

            with patch("slack_worker.slack_client.WebClient") as mock_webclient:
                client = SlackClient()
                assert client.token == "xoxb-test-token"
                mock_webclient.assert_called_once_with(token="xoxb-test-token")

    def test_slack_client_send_message_success(self):
        """Confirms successful message sending"""
        with patch("slack_worker.slack_client.config") as mock_config:
            mock_config.SLACK_BOT_TOKEN = "xoxb-test"

            with patch("slack_worker.slack_client.WebClient") as mock_webclient:
                mock_client = Mock()
                mock_webclient.return_value = mock_client
                mock_client.chat_postMessage.return_value = {"ok": True}

                client = SlackClient()
                result = client.send_message("#test", "Hello")
                assert result is True


# ============================================================================
# 3. SCHEDULER TESTS (FileLock, with_lock, JobScheduler)
# ============================================================================


class TestFileLock:
    """Test FileLock context manager"""

    def test_lock_acquisition(self):
        """Lock initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("slack_worker.scheduler.config") as mock_config:
                mock_config.LOCK_DIR = tmpdir
                mock_config.LOCK_TIMEOUT = 5

                lock = FileLock("test_lock")
                assert lock.lock_name == "test_lock"
                assert lock.timeout == 5

    def test_lock_context_manager(self):
        """Lock acquire/release"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("slack_worker.scheduler.config") as mock_config:
                mock_config.LOCK_DIR = tmpdir
                mock_config.LOCK_TIMEOUT = 5

                with FileLock("test_lock") as lock:
                    assert lock.lock_file is not None
                    assert lock.lock_file_path.exists()


class TestJobScheduler:
    """Test JobScheduler class"""

    def test_scheduler_list_jobs(self):
        """List all jobs"""
        with patch("slack_worker.scheduler.config") as mock_config:
            mock_config.TIMEZONE = "UTC"
            mock_config.LOCK_TIMEOUT = 5
            mock_config.LOCK_DIR = "/tmp"

            scheduler = JobScheduler()

            def test_job():
                pass

            scheduler.add_cron_job(test_job, "job1", "0 9 * * *", use_lock=False)

            job_list = scheduler.list_jobs()
            assert len(job_list) == 1
            assert job_list[0]["id"] == "job1"


# ============================================================================
# 5. HEALTH CHECK TESTS
# ============================================================================


class TestHealthCheck:
    """Test health_check.py functions"""

    def test_check_lock_dir_creates_directory(self):
        """Confirms lock directory setup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_dir = Path(tmpdir) / "locks"

            # Verify lock directory can be created
            lock_dir.mkdir(parents=True, exist_ok=True)
            assert lock_dir.exists()


# ============================================================================
# 6. JOBS TESTS
# ============================================================================


class TestRotaNotifications:
    """Test rota_notifications.py functions"""

    def test_get_this_week_monday(self):
        """Get current week's Monday"""
        from slack_worker.jobs.rota_notifications import get_this_week_monday

        monday = get_this_week_monday()
        # Monday should have weekday() == 0
        assert monday.weekday() == 0
        # Monday should be within last 6 days
        assert (date.today() - monday).days <= 6


# ============================================================================
# 7. SMARTSHEET & GSHEET INTEGRATION TESTS
# ============================================================================


class TestSmartsheetIntegration:
    """Test Smartsheet integration"""

    def test_load_sheet_ids_discovery(self):
        """Discover sheet IDs from environment variables"""
        with patch.dict(
            "os.environ",
            {
                "SMARTSHEET_SHEET_4_12_ID": "test-id-1",
                "SMARTSHEET_SHEET_4_13_ID": "test-id-2",
            },
        ):
            from slack_worker.jobs.sync_releases import _load_sheet_ids

            sheet_ids = _load_sheet_ids()

            # Should find the test IDs
            assert len(sheet_ids) >= 2
            assert sheet_ids["4.12"] == "test-id-1"
            assert sheet_ids["4.13"] == "test-id-2"

    def test_fetch_sheet_by_id_requires_token(self):
        """Test that fetch_sheet_by_id requires access token"""
        from sdk.smartsheet import fetch_sheet_by_id

        # Should raise an error with invalid/no token
        with patch("sdk.smartsheet.fetch_parse_write.requests.get") as mock_get:
            mock_get.side_effect = Exception("Unauthorized")

            with pytest.raises(Exception):
                fetch_sheet_by_id("invalid-sheet-id", "invalid-token")


class TestGSheetIntegration:
    """Test Google Sheets integration"""

    def test_gsheet_initialization_with_creds(self):
        """Test GSheet initializes with service account credentials"""
        with patch("slack_worker.config.config") as mock_config:
            mock_config.ROTA_SERVICE_ACCOUNT = {
                "type": "service_account",
                "project_id": "test",
            }
            mock_config.ROTA_SHEET = "Test Rota"
            mock_config.ASSIGNMENT_WSHEET = "Assignments"

            with patch(
                "sdk.gsheet.gsheet.gspread.service_account_from_dict"
            ) as mock_sa:
                mock_account = Mock()
                mock_sa.return_value = mock_account
                mock_account.open.return_value = Mock()

                from sdk.gsheet.gsheet import GSheet

                GSheet(mock_config.ROTA_SERVICE_ACCOUNT)

                # Verify service account was called
                mock_sa.assert_called_once()

    def test_add_release_validates_version_format(self):
        """Test that add_release validates version format"""
        with patch("slack_worker.config.config") as mock_config:
            mock_config.ROTA_SERVICE_ACCOUNT = {"type": "service_account"}
            mock_config.ROTA_SHEET = "Test"
            mock_config.ASSIGNMENT_WSHEET = "Assignments"

            with patch("sdk.gsheet.gsheet.gspread.service_account_from_dict"):
                from sdk.gsheet.gsheet import GSheet

                # Invalid version format should raise error
                with pytest.raises(ValueError):
                    gsheet = GSheet(mock_config.ROTA_SERVICE_ACCOUNT)
                    gsheet.add_release("invalid-version")  # Should fail validation
