import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from freezegun import freeze_time

from slack_worker.jobs.rota_reminder_job import RotaReminderJob


class TestRotaReminderJob:
    """Test suite for RotaReminderJob."""
    
    @pytest.fixture
    def mock_slack_app(self):
        """Create a mock Slack app."""
        app = Mock()
        app.client = Mock()
        app.client.chat_postMessage = Mock()
        return app
    
    @pytest.fixture
    def mock_lock_manager(self):
        """Create a mock lock manager."""
        manager = Mock()
        manager.acquire_lock = Mock()
        return manager
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        with patch('slack_worker.jobs.rota_reminder_job.config') as mock_cfg:
            mock_cfg.ROTA_USERS = {
                "John Doe": "U123456",
                "Jane Smith": "U234567",
                "Bob Wilson": "U345678"
            }
            mock_cfg.get = Mock(return_value="C987654")
            yield mock_cfg
    
    @pytest.fixture
    def rota_job(self, mock_slack_app, mock_lock_manager, mock_config):
        """Create a RotaReminderJob instance with mocks."""
        with patch.dict('os.environ', {
            'ROTA_GROUP_CHANNEL': 'C987654',
            'ROTA_TEAM_LEADS': 'John Doe,Jane Smith',
            'ROTA_TEAM_MEMBERS': 'Bob Wilson'
        }):
            job = RotaReminderJob(
                slack_app=mock_slack_app,
                lock_manager=mock_lock_manager
            )
            return job
    
    @patch('slack_worker.jobs.rota_reminder_job.gsheet')
    @freeze_time("2024-01-15 09:00:00")  # A Monday
    def test_monday_execution(self, mock_gsheet, rota_job, mock_slack_app):
        """Test that Monday execution posts summary and sends DMs."""
        # Mock gsheet data
        mock_gsheet.fetch_data_by_time.return_value = [
            ["4.15.1", "2024-01-15", "2024-01-19", "John Doe", "Jane Smith", "Bob Wilson", "This Week"]
        ]
        
        # Mock lock manager
        rota_job.lock_manager.acquire_lock = MagicMock()
        rota_job.lock_manager.acquire_lock.return_value.__enter__ = Mock()
        rota_job.lock_manager.acquire_lock.return_value.__exit__ = Mock()
        
        # Execute job
        rota_job.execute()
        
        # Verify gsheet was queried
        assert mock_gsheet.fetch_data_by_time.called
        
        # Verify messages were sent (summary + DMs)
        assert mock_slack_app.client.chat_postMessage.called
    
    @patch('slack_worker.jobs.rota_reminder_job.gsheet')
    @freeze_time("2024-01-18 09:00:00")  # A Thursday
    def test_thursday_execution(self, mock_gsheet, rota_job, mock_slack_app):
        """Test that Thursday execution only posts summary."""
        mock_gsheet.fetch_data_by_time.return_value = [
            ["4.15.1", "2024-01-15", "2024-01-19", "John Doe", "Jane Smith", "Bob Wilson", "This Week"]
        ]
        
        rota_job.lock_manager.acquire_lock = MagicMock()
        rota_job.lock_manager.acquire_lock.return_value.__enter__ = Mock()
        rota_job.lock_manager.acquire_lock.return_value.__exit__ = Mock()
        
        rota_job.execute()
        
        # Verify summary was posted
        assert mock_slack_app.client.chat_postMessage.called
    
    @patch('slack_worker.jobs.rota_reminder_job.gsheet')
    @freeze_time("2024-01-19 16:00:00")  # A Friday
    def test_friday_execution(self, mock_gsheet, rota_job, mock_slack_app):
        """Test that Friday execution sends DMs for next week."""
        mock_gsheet.fetch_data_by_time.return_value = [
            ["4.15.2", "2024-01-22", "2024-01-26", "Jane Smith", "Bob Wilson", "John Doe", "Next Week"]
        ]
        
        rota_job.lock_manager.acquire_lock = MagicMock()
        rota_job.lock_manager.acquire_lock.return_value.__enter__ = Mock()
        rota_job.lock_manager.acquire_lock.return_value.__exit__ = Mock()
        
        rota_job.execute()
        
        # Verify DMs were sent
        assert mock_slack_app.client.chat_postMessage.called
    
    @patch('slack_worker.jobs.rota_reminder_job.gsheet')
    @freeze_time("2024-01-17 12:00:00")  # A Wednesday (no scheduled action)
    def test_no_action_on_other_days(self, mock_gsheet, rota_job, mock_slack_app):
        """Test that no action is taken on days without scheduled reminders."""
        rota_job.lock_manager.acquire_lock = MagicMock()
        rota_job.lock_manager.acquire_lock.return_value.__enter__ = Mock()
        rota_job.lock_manager.acquire_lock.return_value.__exit__ = Mock()
        
        rota_job.execute()
        
        # No messages should be sent
        assert not mock_slack_app.client.chat_postMessage.called
    
    def test_get_slack_mention(self, rota_job):
        """Test Slack mention formatting."""
        mention = rota_job._get_slack_mention("John Doe")
        assert mention == "<@U123456>"
        
        mention_unknown = rota_job._get_slack_mention("Unknown Person")
        assert mention_unknown == "Unknown Person"
        
        mention_none = rota_job._get_slack_mention(None)
        assert mention_none == "TBD"
    
    @patch('slack_worker.jobs.rota_reminder_job.gsheet')
    def test_post_summary_with_no_data(self, mock_gsheet, rota_job, mock_slack_app):
        """Test posting summary when no releases are found."""
        mock_gsheet.fetch_data_by_time.return_value = []
        
        rota_job._post_rota_summary("This Week")
        
        # Should still post a message indicating no releases
        assert mock_slack_app.client.chat_postMessage.called
        call_args = mock_slack_app.client.chat_postMessage.call_args
        assert "No releases" in call_args[1]['text']

