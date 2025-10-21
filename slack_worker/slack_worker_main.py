"""
Slack Worker - Scheduled Task Manager
=====================================
This service handles scheduled batch jobs for the Slack bot, including:
- ROTA reminders and notifications
- Future scheduled reporting tasks
- Any batch operations that need to run on a schedule

Architecture:
- Uses APScheduler for job scheduling
- Supports horizontal scaling with file-based locking
- Each job is independently defined and schedulable
- Integrates with Slack Bot API for posting messages
"""

import logging
import os
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from slack_bolt import App

# Add parent directory to path to import shared config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from slack_worker.jobs.rota_reminder_job import RotaReminderJob
from slack_worker.utils.lock_manager import LockManager

# Configure logging
logger = logging.getLogger(__name__)


class SlackWorker:
    """
    Main worker class that manages scheduled jobs.
    
    This class initializes the scheduler, registers jobs, and handles
    execution coordination across multiple instances using file locks.
    """
    
    def __init__(self):
        """Initialize the Slack Worker with scheduler and Slack app."""
        self.scheduler = BlockingScheduler(
            timezone=os.getenv("TIMEZONE", "UTC")
        )
        
        # Initialize Slack app for posting messages
        self.slack_app = App(token=config.SLACK_BOT_TOKEN)
        
        # Initialize lock manager for distributed coordination
        lock_dir = os.getenv("LOCK_DIR", "/tmp/slack_worker_locks")
        self.lock_manager = LockManager(lock_dir=lock_dir)
        
        # Job registry - add new jobs here
        self.jobs = []
        
        logger.info("Slack Worker initialized")
    
    def register_jobs(self):
        """
        Register all scheduled jobs with the scheduler.
        
        Each job should be independently defined and have its own:
        - Job class with execute() method
        - Schedule configuration (cron expression)
        - Unique job ID
        """
        
        # ROTA Reminder Job
        rota_job = RotaReminderJob(
            slack_app=self.slack_app,
            lock_manager=self.lock_manager
        )
        self.jobs.append(rota_job)
        
        # Schedule: Monday at 9:00 AM - Post week's releases + DM participants
        self.scheduler.add_job(
            func=rota_job.execute,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
            id='rota_monday_reminder',
            name='ROTA Monday Reminder',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Registered job: ROTA Monday Reminder (Mon 9:00 AM)")
        
        # Schedule: Thursday at 9:00 AM - Post week's releases
        self.scheduler.add_job(
            func=rota_job.execute,
            trigger=CronTrigger(day_of_week='thu', hour=9, minute=0),
            id='rota_thursday_reminder',
            name='ROTA Thursday Reminder',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Registered job: ROTA Thursday Reminder (Thu 9:00 AM)")
        
        # Schedule: Friday at 4:00 PM - DM next week's participants
        self.scheduler.add_job(
            func=rota_job.execute,
            trigger=CronTrigger(day_of_week='fri', hour=16, minute=0),
            id='rota_friday_reminder',
            name='ROTA Friday Reminder',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Registered job: ROTA Friday Reminder (Fri 4:00 PM)")
        
        # Example: Add more jobs here as needed
        # self._register_weekly_report_job()
        # self._register_metrics_job()
        
    def _register_weekly_report_job(self):
        """
        Example: Register a weekly reporting job.
        This is a placeholder for future batch jobs.
        """
        # TODO: Implement weekly report job
        # weekly_report_job = WeeklyReportJob(
        #     slack_app=self.slack_app,
        #     lock_manager=self.lock_manager
        # )
        # self.scheduler.add_job(
        #     func=weekly_report_job.execute,
        #     trigger=CronTrigger(day_of_week='mon', hour=10, minute=0),
        #     id='weekly_report',
        #     name='Weekly Report',
        #     replace_existing=True
        # )
        pass
    
    def _job_listener(self, event):
        """
        Listen to job execution events for logging and monitoring.
        
        Args:
            event: APScheduler event object
        """
        if event.exception:
            logger.error(
                f"Job {event.job_id} failed with exception: {event.exception}",
                exc_info=event.exception
            )
        else:
            logger.info(f"Job {event.job_id} executed successfully")
    
    def start(self):
        """
        Start the worker and begin processing scheduled jobs.
        
        This is a blocking call that runs until interrupted.
        """
        logger.info("=" * 60)
        logger.info("Starting Slack Worker Service")
        logger.info(f"Timezone: {self.scheduler.timezone}")
        logger.info(f"Lock Directory: {self.lock_manager.lock_dir}")
        logger.info("=" * 60)
        
        # Register all jobs
        self.register_jobs()
        
        # Add event listener for job execution
        self.scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        # Print scheduled jobs
        logger.info("Scheduled Jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.name} (ID: {job.id})")
            logger.info(f"    Next run: {job.next_run_time}")
        
        logger.info("=" * 60)
        
        try:
            # Start the scheduler (blocking)
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down Slack Worker...")
            self.scheduler.shutdown()
            logger.info("Slack Worker stopped")


def main():
    """Main entry point for the Slack Worker service."""
    try:
        worker = SlackWorker()
        worker.start()
    except Exception as e:
        logger.exception(f"Fatal error in Slack Worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

