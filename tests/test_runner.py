from pytest import Pytester


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
