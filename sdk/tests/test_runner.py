from pytest import Pytester


class TestRunner(object):
    def test_aws(self, pytester: Pytester) -> None:
        pytester.copy_example("tests/test_aws.py")
        result = pytester.runpytest()
        outcomes = result.parseoutcomes()
        assert "failed" not in outcomes.keys(), (
            f"{outcomes['failed']} unit tests failed."
        )
        assert "errors" not in outcomes.keys(), (
            f"{outcomes['errors']} unit tests have errors."
        )
        assert "passed" in outcomes.keys(), "No tests passed."

    def test_openstack(self, pytester: Pytester) -> None:
        pytester.copy_example("tests/test_openstack.py")
        result = pytester.runpytest()
        outcomes = result.parseoutcomes()
        assert "failed" not in outcomes.keys(), (
            f"{outcomes['failed']} unit tests failed."
        )
        assert "errors" not in outcomes.keys(), (
            f"{outcomes['errors']} unit tests have errors."
        )
        assert "passed" in outcomes.keys(), "No tests passed."

    def test_tools(self, pytester: Pytester) -> None:
        pytester.copy_example("tests/test_tools.py")
        result = pytester.runpytest()
        outcomes = result.parseoutcomes()
        assert "failed" not in outcomes.keys(), (
            f"{outcomes['failed']} unit tests failed."
        )
        assert "errors" not in outcomes.keys(), (
            f"{outcomes['errors']} unit tests have errors."
        )
        assert "passed" in outcomes.keys(), "No tests passed."
