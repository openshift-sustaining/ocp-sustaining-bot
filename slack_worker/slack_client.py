"""
Slack client for sending messages
"""

import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .config import config

logger = logging.getLogger(__name__)


class SlackClient:
    """Wrapper for Slack Web API client"""

    def __init__(self, token: str = None):
        """
        Initialize Slack client

        Args:
            token: Slack bot token (defaults to config)
        """
        self.token = token or config.SLACK_BOT_TOKEN
        self.client = WebClient(token=self.token)

    def send_message(self, channel: str, text: str = None, blocks: list = None) -> bool:
        """
        Send a message to a channel or user

        Args:
            channel: Channel ID or user ID
            text: Plain text message
            blocks: Slack blocks for rich formatting

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.client.chat_postMessage(
                channel=channel, text=text, blocks=blocks
            )

            if response["ok"]:
                logger.info(f"Message sent successfully to {channel}")
                return True
            else:
                logger.error(f"Failed to send message to {channel}: {response}")
                return False

        except SlackApiError as e:
            logger.error(
                f"Slack API error sending message to {channel}: {e.response['error']}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to {channel}: {e}")
            return False

    def send_dm(self, user_id: str, text: str = None, blocks: list = None) -> bool:
        """
        Send a direct message to a user

        Args:
            user_id: Slack user ID
            text: Plain text message
            blocks: Slack blocks for rich formatting

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Open a DM channel with the user
            response = self.client.conversations_open(users=[user_id])

            if not response["ok"]:
                logger.error(f"Failed to open DM channel with {user_id}")
                return False

            channel_id = response["channel"]["id"]

            # Send message to the DM channel
            return self.send_message(channel_id, text=text, blocks=blocks)

        except SlackApiError as e:
            logger.error(
                f"Slack API error sending DM to {user_id}: {e.response['error']}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending DM to {user_id}: {e}")
            return False

    def get_user_info(self, user_id: str) -> dict:
        """
        Get user information

        Args:
            user_id: Slack user ID

        Returns:
            dict: User information
        """
        try:
            response = self.client.users_info(user=user_id)

            if response["ok"]:
                return response["user"]
            else:
                logger.error(f"Failed to get user info for {user_id}")
                return {}

        except SlackApiError as e:
            logger.error(
                f"Slack API error getting user info for {user_id}: {e.response['error']}"
            )
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting user info for {user_id}: {e}")
            return {}


# Global slack client instance
slack_client = SlackClient()
