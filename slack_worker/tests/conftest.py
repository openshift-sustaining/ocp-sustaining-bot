import pytest
import sys
import os
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """
    Set up mock environment variables for testing.
    
    This fixture automatically applies to all tests.
    """
    # Mock essential environment variables
    test_env = {
        'SLACK_BOT_TOKEN': 'xoxb-test-token',
        'SLACK_APP_TOKEN': 'xapp-test-token',
        'ROTA_GROUP_CHANNEL': 'C123456789',
        'ROTA_TEAM_LEADS': 'Lead1,Lead2',
        'ROTA_TEAM_MEMBERS': 'Member1,Member2,Member3',
        'LOG_LEVEL': 'INFO',
        'TIMEZONE': 'UTC',
        'LOCK_DIR': '/tmp/test_locks'
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def sample_rota_data():
    """
    Provide sample ROTA data for testing.
    
    Returns:
        list: Sample ROTA data in the format returned by gsheet
    """
    return [
        ["4.15.1", "2024-01-15", "2024-01-19", "John Doe", "Jane Smith", "Bob Wilson", "This Week"],
        ["4.15.2", "2024-01-22", "2024-01-26", "Alice Brown", "Charlie Davis", "Eve White", "Next Week"]
    ]


@pytest.fixture
def mock_slack_client():
    """
    Create a mock Slack client for testing.
    
    Returns:
        Mock: Mock Slack client object
    """
    from unittest.mock import Mock
    
    client = Mock()
    client.chat_postMessage = Mock(return_value={'ok': True})
    
    return client

