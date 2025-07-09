from pytest import Pytester


class TestRunner(object):
    def test_handlers(self, pytester: Pytester) -> None:
        """Test the slack handlers."""
        pytester.copy_example("test_handlers.py")
        result = pytester.runpytest()
        outcomes = result.parseoutcomes()
        assert "failed" not in outcomes.keys(), (
            f"{outcomes['failed']} unit tests failed."
        )
        assert "errors" not in outcomes.keys(), (
            f"{outcomes['errors']} unit tests have errors."
        )
        assert "passed" in outcomes.keys(), "No tests passed."
