import logging
from abc import ABC, abstractmethod
from typing import Optional
from slack_bolt import App
from slack_worker.utils.lock_manager import LockManager

logger = logging.getLogger(__name__)


class BaseJob(ABC):
    """
    Abstract base class for scheduled jobs.
    
    All jobs should inherit from this class and implement the execute() method.
    This provides a consistent interface and common functionality.
    """
    
    def __init__(
        self,
        slack_app: App,
        lock_manager: Optional[LockManager] = None
    ):
        """
        Initialize the base job.
        
        Args:
            slack_app: Slack Bolt App instance for posting messages
            lock_manager: Lock manager for distributed coordination (optional)
        """
        self.slack_app = slack_app
        self.lock_manager = lock_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def execute(self):
        """
        Execute the job.
        
        This method must be implemented by all subclasses.
        It should contain the main logic of the job.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def get_job_name(self) -> str:
        """
        Get the name of the job.
        
        Returns:
            str: The job name (class name by default)
        """
        return self.__class__.__name__
    
    def post_to_slack(self, channel: str, message: str):
        """
        Helper method to post a message to Slack.
        
        Args:
            channel: Channel ID or user ID to post to
            message: Message text to post
        """
        try:
            self.slack_app.client.chat_postMessage(
                channel=channel,
                text=message
            )
            self.logger.info(f"Posted message to {channel}")
        except Exception as e:
            self.logger.error(f"Failed to post to Slack: {e}")
            raise
    
    def post_blocks_to_slack(self, channel: str, blocks: list, text: str = ""):
        """
        Helper method to post formatted blocks to Slack.
        
        Args:
            channel: Channel ID or user ID to post to
            blocks: List of Slack block elements
            text: Fallback text for notifications
        """
        try:
            self.slack_app.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=text
            )
            self.logger.info(f"Posted blocks to {channel}")
        except Exception as e:
            self.logger.error(f"Failed to post blocks to Slack: {e}")
            raise

