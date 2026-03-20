from pytest import Pytester
from unittest.mock import Mock
import sys

# Mock config module so that no connections are made at import time leading to exceptions
sys.modules["config"] = Mock()
sys.modules["gspread"] = Mock()

# fmt: off
from config import config  # noqa
config.ALLOWED_SLACK_USERS = {"test_user": "U123456"}
config.GCP_POPULAR_INSTANCE_TYPES = [
    "e2-micro",
    "e2-medium",
    "n2-standard-4",
]
config.GCP_BOOT_DISK_SIZE_GB = 10
config.GCP_DEFAULT_INSTANCE_TYPE = "e2-medium"
# fmt: on


class TestRunner(object):
    def test_handlers(self, pytester: Pytester) -> None:
        """Test the slack handlers."""
        pytester.copy_example("tests/test_handlers.py")
        result = pytester.runpytest()
        outcomes = result.parseoutcomes()
        assert "failed" not in outcomes.keys(), (
            f"{outcomes['failed']} unit tests failed."
        )
        assert "errors" not in outcomes.keys(), (
            f"{outcomes['errors']} unit tests have errors."
        )
        assert "passed" in outcomes.keys(), "No tests passed."

    def test_slack_commands(self, pytester: Pytester) -> None:
        """Test the slack commands."""
        pytester.copy_example("tests/test_slack_commands.py")
        result = pytester.runpytest()
        outcomes = result.parseoutcomes()
        assert "failed" not in outcomes.keys(), (
            f"{outcomes['failed']} unit tests failed."
        )
        assert "errors" not in outcomes.keys(), (
            f"{outcomes['errors']} unit tests have errors."
        )
        assert "passed" in outcomes.keys(), "No tests passed."
