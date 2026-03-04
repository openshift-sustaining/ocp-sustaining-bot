"""
Main entry point for Slack Worker Service
Initializes and starts the job scheduler with configured jobs
"""

import logging
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slack_worker.config import config, validate_config
from slack_worker.jobs import (
    send_rota_notifications,
    sync_releases_to_gsheet,
)
from slack_worker.scheduler import JobScheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def setup_jobs(scheduler: JobScheduler):
    """
    Set up all scheduled jobs

    Args:
        scheduler: JobScheduler instance
    """
    logger.info("Setting up scheduled jobs...")

    # 1. Sync releases job (runs first - before notifications)
    if config.SCHEDULE_ROTA_SHEET_SYNC:
        scheduler.add_cron_job(
            func=sync_releases_to_gsheet,
            job_id="sync_releases_to_gsheet",
            cron_expression=config.SCHEDULE_ROTA_SHEET_SYNC,
            use_lock=True,
        )
        logger.info(f"Enabled: Sync releases job ({config.SCHEDULE_ROTA_SHEET_SYNC})")
    else:
        logger.info("Disabled: Sync releases job (empty schedule)")

    # 2. Notifications job (runs second - after sync)
    if config.SCHEDULE_ROTA_NOTIFICATIONS:
        scheduler.add_cron_job(
            func=send_rota_notifications,
            job_id="send_rota_notifications",
            cron_expression=config.SCHEDULE_ROTA_NOTIFICATIONS,
            use_lock=True,
        )
        logger.info(
            f"Enabled: ROTA notifications job ({config.SCHEDULE_ROTA_NOTIFICATIONS})"
        )
    else:
        logger.info("Disabled: ROTA notifications job (empty schedule)")

    logger.info(
        f"Job setup complete. Total jobs scheduled: {len(scheduler.scheduler.get_jobs())}"
    )


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Starting Slack Worker Service")
    logger.info("=" * 60)

    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()

        # Create lock directory if it doesn't exist
        lock_dir = Path(config.LOCK_DIR)
        lock_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Lock directory: {lock_dir}")

        # Initialize scheduler
        logger.info(f"Initializing scheduler (timezone: {config.TIMEZONE})...")
        scheduler = JobScheduler(timezone=config.TIMEZONE)

        # Set up jobs
        setup_jobs(scheduler)

        # List all scheduled jobs
        logger.info("Scheduled jobs:")
        scheduler.list_jobs()

        # Start scheduler (blocking)
        logger.info("=" * 60)
        logger.info("Slack Worker Service is running")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        scheduler.start()

    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Slack Worker Service stopped")


if __name__ == "__main__":
    main()
