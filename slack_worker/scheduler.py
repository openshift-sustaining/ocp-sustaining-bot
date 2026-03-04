"""
Job Scheduler with APScheduler and file-based locking for horizontal scaling
"""

import fcntl
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import pytz
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import config

logger = logging.getLogger(__name__)


class FileLock:
    """
    File-based lock for preventing duplicate job execution in horizontally scaled environments.
    Uses flock for advisory locking across processes/containers via shared PVC.
    """

    def __init__(self, lock_name: str, timeout: int = None):
        """
        Initialize file lock

        Args:
            lock_name: Name of the lock (used for lock file name)
            timeout: Lock timeout in seconds
        """
        self.lock_name = lock_name
        self.timeout = timeout or config.LOCK_TIMEOUT
        self.lock_dir = Path(config.LOCK_DIR)
        self.lock_file_path = self.lock_dir / f"{lock_name}.lock"
        self.lock_file = None

        # Create lock directory if it doesn't exist
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        """Acquire lock"""
        try:
            self.lock_file = open(self.lock_file_path, "w")

            # Try to acquire lock with timeout
            start_time = time.time()
            while True:
                try:
                    # Non-blocking exclusive lock
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                    # Write PID and timestamp to lock file
                    self.lock_file.write(f"PID: {os.getpid()}\n")
                    self.lock_file.write(f"Acquired: {datetime.now().isoformat()}\n")
                    self.lock_file.flush()

                    logger.debug(f"Acquired lock: {self.lock_name}")
                    return self

                except BlockingIOError:
                    # Lock is held by another process
                    if time.time() - start_time > self.timeout:
                        raise TimeoutError(
                            f"Could not acquire lock {self.lock_name} within {self.timeout} seconds"
                        )
                    time.sleep(0.1)  # Wait a bit before retrying

        except Exception as e:
            if self.lock_file:
                self.lock_file.close()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock"""
        try:
            if self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                logger.debug(f"Released lock: {self.lock_name}")
        except Exception as e:
            logger.error(f"Error releasing lock {self.lock_name}: {e}")

        return False


def with_lock(lock_name: str):
    """
    Decorator to wrap a job function with file locking

    Args:
        lock_name: Name of the lock
    """

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            try:
                with FileLock(lock_name):
                    logger.info(f"Executing job: {func.__name__}")
                    result = func(*args, **kwargs)
                    logger.info(f"Completed job: {func.__name__}")
                    return result
            except TimeoutError as e:
                logger.warning(
                    f"Job {func.__name__} skipped - another instance is running: {e}"
                )
                return None
            except Exception as e:
                logger.error(f"Error in job {func.__name__}: {e}", exc_info=True)
                raise

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


class JobScheduler:
    """
    Job scheduler with APScheduler and file-based locking support
    """

    def __init__(self, timezone: str = None):
        """
        Initialize job scheduler

        Args:
            timezone: Timezone for scheduling (default from config)
        """
        self.timezone = timezone or config.TIMEZONE
        self.scheduler = BlockingScheduler(timezone=self.timezone)

        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

        logger.info(f"Initialized job scheduler with timezone: {self.timezone}")

    def _job_executed(self, event):
        """Event listener for successful job execution"""
        logger.info(f"Job {event.job_id} executed successfully")

    def _job_error(self, event):
        """Event listener for job errors"""
        logger.error(f"Job {event.job_id} raised an exception: {event.exception}")

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        cron_expression: str,
        use_lock: bool = True,
        **kwargs,
    ):
        """
        Add a cron job to the scheduler

        Args:
            func: Function to execute
            job_id: Unique job identifier
            cron_expression: Cron expression (e.g., '0 9 * * MON,THU')
            use_lock: Whether to use file locking (for horizontal scaling)
            **kwargs: Additional arguments to pass to the job
        """
        # Wrap function with lock if needed
        if use_lock:
            func = with_lock(f"job_{job_id}")(func)

        # Parse cron expression
        # Format: minute hour day month day_of_week
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        minute, hour, day, month, day_of_week = parts

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=self.timezone,
        )

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=func.__name__,
            kwargs=kwargs,
            replace_existing=True,
            max_instances=1,  # Prevent concurrent execution of same job
        )

        logger.info(
            f"Added cron job: {job_id} ({func.__name__}) "
            f"with schedule: {cron_expression} (lock: {use_lock})"
        )

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: int = None,
        minutes: int = None,
        hours: int = None,
        use_lock: bool = True,
        **kwargs,
    ):
        """
        Add an interval-based job to the scheduler

        Args:
            func: Function to execute
            job_id: Unique job identifier
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            use_lock: Whether to use file locking
            **kwargs: Additional arguments to pass to the job
        """
        if use_lock:
            func = with_lock(f"job_{job_id}")(func)

        # Build interval kwargs, excluding None values
        interval_kwargs = {}
        if seconds is not None:
            interval_kwargs["seconds"] = seconds
        if minutes is not None:
            interval_kwargs["minutes"] = minutes
        if hours is not None:
            interval_kwargs["hours"] = hours

        self.scheduler.add_job(
            func,
            "interval",
            **interval_kwargs,
            id=job_id,
            name=func.__name__,
            kwargs=kwargs,
            replace_existing=True,
            max_instances=1,
        )

        interval_str = (
            f"{seconds}s" if seconds else f"{minutes}m" if minutes else f"{hours}h"
        )
        logger.info(
            f"Added interval job: {job_id} ({func.__name__}) "
            f"with interval: {interval_str} (lock: {use_lock})"
        )

    def start(self):
        """Start the scheduler"""
        logger.info("Starting job scheduler...")
        logger.info(f"Scheduled jobs: {len(self.scheduler.get_jobs())}")

        for job in self.scheduler.get_jobs():
            # Get next run time from trigger if available
            next_run = getattr(
                job, "next_run_time", None
            ) or job.trigger.get_next_fire_time(None, datetime.now(pytz.UTC))
            logger.info(f"  - {job.id}: {job.name} (next run: {next_run})")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.shutdown()

    def shutdown(self):
        """Shutdown the scheduler"""
        logger.info("Shutting down job scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("Job scheduler stopped")

    def list_jobs(self):
        """List all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            logger.info("No jobs scheduled")
            return []

        job_list = []
        for job in jobs:
            job_info = {
                "id": job.id,
                "name": job.name,
                "next_run": getattr(job, "next_run_time", None),
                "trigger": str(job.trigger),
            }
            job_list.append(job_info)
            logger.info(f"Job: {job_info}")

        return job_list
