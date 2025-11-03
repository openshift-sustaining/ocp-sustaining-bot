"""
ROTA Reminder Job
=================
Handles automated ROTA reminders and notifications.

Schedule:
- Monday 9:00 AM: Post week's releases to group + DM participants
- Thursday 9:00 AM: Post week's releases to group
- Friday 4:00 PM: DM next week's participants
"""

import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config
from slack_worker.jobs.base_job import BaseJob
from slack_worker.gsheet.gsheet import gsheet
from filelock import Timeout

logger = logging.getLogger(__name__)


class RotaReminderJob(BaseJob):
    """
    Job for sending automated ROTA reminders.
    
    This job handles:
    1. Posting release summaries to group channels
    2. Sending DM reminders to assigned team members
    3. Updating the intermediary Google Sheet for history
    """
    
    def __init__(self, slack_app, lock_manager):
        """
        Initialize the ROTA Reminder Job.
        
        Args:
            slack_app: Slack Bolt App instance
            lock_manager: Lock manager for distributed coordination
        """
        super().__init__(slack_app, lock_manager)
        
        # Get configuration from environment
        self.group_channel = os.getenv(
            "ROTA_GROUP_CHANNEL",
            config.get("ROTA_GROUP_CHANNEL", "")
        )
        
        # Team configuration (from environment or config)
        self.team_leads = self._get_list_from_env("ROTA_TEAM_LEADS", [])
        self.team_members = self._get_list_from_env("ROTA_TEAM_MEMBERS", [])
        
        # Intermediary sheet for history/reference
        self.history_sheet_name = os.getenv(
            "ROTA_HISTORY_SHEET",
            "ROTA_History"
        )
    
    def _get_list_from_env(self, env_var: str, default: list) -> list:
        """
        Get a comma-separated list from environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            list: List of values
        """
        value = os.getenv(env_var, "")
        if value:
            return [item.strip() for item in value.split(",")]
        return default
    
    def execute(self):
        """
        Execute the ROTA reminder job.
        
        This method determines what action to take based on the current day:
        - Monday: Post summary + DM current week participants
        - Thursday: Post summary
        - Friday: DM next week participants
        """
        job_lock_id = f"rota_reminder_{datetime.now().strftime('%Y-%m-%d')}"
        
        # Use lock to prevent duplicate execution in scaled environments
        try:
            with self.lock_manager.acquire_lock(job_lock_id, timeout=5):
                self.logger.info("Acquired lock for ROTA reminder job")
                self._execute_reminder()
        except Timeout:
            self.logger.warning(
                "Could not acquire lock - job likely running on another instance"
            )
        except Exception as e:
            self.logger.exception(f"Error executing ROTA reminder: {e}")
            raise
    
    def _execute_reminder(self):
        """Internal method to execute the actual reminder logic."""
        today = datetime.now()
        weekday = today.weekday()  # Monday = 0, Thursday = 3, Friday = 4
        
        self.logger.info(f"Running ROTA reminder for {today.strftime('%A, %Y-%m-%d')}")
        
        if not gsheet:
            self.logger.error("GSheet not initialized - cannot send reminders")
            return
        
        try:
            if weekday == 0:  # Monday
                self.logger.info("Monday: Posting summary + sending DMs for This Week")
                self._post_rota_summary("This Week")
                self._dm_rota_participants("This Week")
                self._update_history_sheet("This Week")
                
            elif weekday == 3:  # Thursday
                self.logger.info("Thursday: Posting summary for This Week")
                self._post_rota_summary("This Week")
                
            elif weekday == 4:  # Friday
                self.logger.info("Friday: Sending DMs for Next Week")
                self._dm_rota_participants("Next Week")
                
            else:
                self.logger.info(f"No ROTA reminder scheduled for {today.strftime('%A')}")
                
        except Exception as e:
            self.logger.exception(f"Error in ROTA reminder execution: {e}")
            raise
    
    def _post_rota_summary(self, period: str):
        """
        Post a formatted summary of releases to the group channel.
        
        Args:
            period: "This Week" or "Next Week"
        """
        if not self.group_channel:
            self.logger.warning("No group channel configured - skipping summary post")
            return
        
        try:
            data = gsheet.fetch_data_by_time(period)
        except ValueError as e:
            self.logger.error(f"Invalid period for rota summary: {e}")
            return
        
        if not data:
            message = f"📢 *{period}'s Releases:*\n\nNo releases scheduled for {period.lower()}."
            self.post_to_slack(self.group_channel, message)
            return
        
        # Format the message
        header = f"📢 *{period}'s Releases:*"
        releases = []
        
        for row in data:
            if len(row) != 7:
                continue
            
            rel_ver, s_date, e_date, pm, qe1, qe2, _ = row
            
            if rel_ver == "N/A":
                continue
            
            # Convert names to Slack mentions
            pm_mention = self._get_slack_mention(pm)
            qe1_mention = self._get_slack_mention(qe1)
            qe2_mention = self._get_slack_mention(qe2)
            
            release_info = (
                f"*Release:* {rel_ver}\n"
                f"*Dates:* {s_date or 'TBD'} → {e_date or 'TBD'}\n"
                f"*Patch Manager:* {pm_mention}\n"
                f"*QE:* {qe1_mention}, {qe2_mention}"
            )
            releases.append(release_info)
        
        if not releases:
            message = f"{header}\n\nNo releases scheduled for {period.lower()}."
        else:
            message = f"{header}\n\n" + "\n\n".join(releases)
        
        self.post_to_slack(self.group_channel, message)
        self.logger.info(f"Posted {period} release summary to group channel")
    
    def _dm_rota_participants(self, period: str):
        """
        Send direct messages to people assigned to releases.
        
        Args:
            period: "This Week" or "Next Week"
        """
        try:
            data = gsheet.fetch_data_by_time(period)
        except ValueError as e:
            self.logger.error(f"Invalid period for rota DMs: {e}")
            return
        
        if not data:
            self.logger.info(f"No releases found for {period}, skipping DMs")
            return
        
        sent = set()
        
        for row in data:
            if len(row) != 7:
                continue
            
            rel_ver, s_date, e_date, pm, qe1, qe2, _ = row
            
            if rel_ver == "N/A":
                continue
            
            # Send DM to each participant
            for name in (pm, qe1, qe2):
                if not name or name in sent:
                    continue
                
                sent.add(name)
                
                slack_id = config.ROTA_USERS.get(name)
                if not slack_id:
                    self.logger.warning(f"No Slack ID found for {name}. Skipping.")
                    continue
                
                message = (
                    f"👋 Hi <@{slack_id}>! Reminder: You're assigned to *{rel_ver}* "
                    f"({period}).\n\n"
                    f"*Dates:* start : {s_date or 'TBD'} → end: {e_date or 'TBD'}\n\n"
                    f"If you have any questions or need to make changes, "
                    f"please contact the patch manager."
                )
                
                try:
                    self.post_to_slack(slack_id, message)
                except Exception as e:
                    self.logger.error(f"Failed to send DM to {name}: {e}")
        
        self.logger.info(f"Sent {len(sent)} DM reminders for {period}")
    
    def _get_slack_mention(self, name: str) -> str:
        """
        Convert a name to a Slack mention format.
        
        Args:
            name: Person's name
            
        Returns:
            str: Slack mention or original name
        """
        if not name:
            return "TBD"
        
        slack_id = config.ROTA_USERS.get(name)
        if slack_id:
            return f"<@{slack_id}>"
        return name
    
   