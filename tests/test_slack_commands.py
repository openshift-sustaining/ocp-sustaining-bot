import os
from unittest.mock import MagicMock, patch

os.environ["SLACK_BOT_TOKEN"] = "fake-token-for-testing"
os.environ["SLACK_APP_TOKEN"] = "fake-token-for-testing"

import sys

with patch("slack_sdk.web.client.WebClient.auth_test", return_value={"ok": True}):
    if "slack_main" in sys.modules:
        del sys.modules["slack_main"]
    from slack_main import mention_handler


class MockCommand:
    """Helper class to create reusable mock setups for commands"""

    @staticmethod
    def setup_mocks():
        """Set up all necessary mocks for mention_handler testing - only command handlers"""
        return {
            "handle_create_openstack_vm": patch(
                "slack_main.handle_create_openstack_vm"
            ),
            "handle_list_openstack_vms": patch("slack_main.handle_list_openstack_vms"),
            "handle_hello": patch("slack_main.handle_hello"),
            "handle_create_aws_vm": patch("slack_main.handle_create_aws_vm"),
            "handle_list_aws_vms": patch("slack_main.handle_list_aws_vms"),
            "handle_aws_modify_vm": patch("slack_main.handle_aws_modify_vm"),
            "handle_list_team_links": patch("slack_main.handle_list_team_links"),
            "handle_help_command": patch("slack_main.handle_help_command"),
        }

    @staticmethod
    def create_mock_body(text="hello", user="U123456"):
        """Create a mock Slack body event"""
        return {"event": {"user": user, "text": text}}


class TestSlackCommands:
    """Test class for the slack commands"""

    def setup_method(self):
        self.mock_say = MagicMock()
        self.mocks = MockCommand.setup_mocks()

        for mock_name, mock_patch in self.mocks.items():
            setattr(self, f"mock_{mock_name}", mock_patch.start())

    def teardown_method(self):
        for mock_patch in self.mocks.values():
            mock_patch.stop()

    def call_mention_handler(self, command_text, user="U123456"):
        """Helper method to create body and call mention_handler"""
        body = MockCommand.create_mock_body(command_text, user)
        mention_handler(body, self.mock_say)

    def test_hello_command_success(self):
        """Test successful hello command execution"""
        self.call_mention_handler("hello")

        self.mock_handle_hello.assert_called_once()

    def test_aws_vm_create_command_success(self):
        """Test successful AWS VM create command execution"""
        self.call_mention_handler(
            "@bot aws vm create --os_name=linux --instance_type=t2.micro --key_pair=new"
        )

        self.mock_handle_create_aws_vm.assert_called_once()

    def test_openstack_vm_create_command_success(self):
        """Test successful OpenStack VM create command execution"""
        self.call_mention_handler(
            "@bot openstack vm create --name=test --os_name=fedora --flavor=ci.cpu.small --key_pair=new"
        )

        self.mock_handle_create_openstack_vm.assert_called_once()

    def test_invalid_command(self):
        """Test invalid command input"""
        self.call_mention_handler("")

        self.mock_say.assert_called_once()
        call_args = self.mock_say.call_args[0][0]
        assert "couldn't understand" in call_args
        assert "help" in call_args

    def test_unknown_command(self):
        """Test unknown command handling"""
        self.call_mention_handler("@bot unknown param")

        self.mock_say.assert_called_once()
        call_args = self.mock_say.call_args[0][0]
        assert "couldn't understand" in call_args

    def test_help_flag_command(self):
        """Test help flag handling"""
        self.call_mention_handler("@bot aws vm create --help")

        self.mock_handle_help_command.assert_called_once()

    def test_aws_vm_modify_with_multiple_parameters(self):
        """Test AWS VM modify command with multiple parameters"""
        self.call_mention_handler("@bot aws vm modify --stop --vm-id=i-123456")

        self.mock_handle_aws_modify_vm.assert_called_once()

    def test_aws_vm_list_with_filters(self):
        """Test AWS VM list command with filter parameters"""
        self.call_mention_handler(
            "@bot aws vm list --state=running,stopped --type=t2.micro"
        )

        self.mock_handle_list_aws_vms.assert_called_once()

    def test_openstack_vm_list_with_status(self):
        """Test OpenStack VM list command with status filter"""
        self.call_mention_handler("@bot openstack vm list --status=ACTIVE")

        self.mock_handle_list_openstack_vms.assert_called_once()

    def test_project_links_list_command(self):
        """Test project links list command"""
        self.call_mention_handler("@bot project links list")

        self.mock_handle_list_team_links.assert_called_once_with(
            self.mock_say, "U123456"
        )

    def test_command_with_nonexistent_parameters(self):
        """Test command with non-existent parameters"""
        self.call_mention_handler(
            "@bot aws vm create --invalid_param=value --os_name=linux"
        )

        self.mock_handle_create_aws_vm.assert_called_once()

    def test_command_with_typo(self):
        """Test command with a typo"""
        self.call_mention_handler(
            "aws vm creaate --invalid_param=value --os_name=linux"
        )

        self.mock_handle_create_aws_vm.assert_not_called()
        self.mock_say.assert_called_once()
        call_args = self.mock_say.call_args[0][0]
        assert "couldn't understand" in call_args

    def test_empty_body_event(self):
        """Test handling of empty or malformed body event"""
        body = {}

        mention_handler(body, self.mock_say)

    def test_missing_event_data(self):
        """Test handling of missing event data"""
        body = {"event": {}}

        mention_handler(body, self.mock_say)
