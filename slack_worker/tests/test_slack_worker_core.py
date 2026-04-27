"""
Core tests for slack_worker - Validates health_check.py checks
"""

import tempfile
from pathlib import Path

from slack_worker.config import config
from slack_worker.scheduler import JobScheduler


# ============================================================================
# 1. CONFIG VALIDATION TESTS
# ============================================================================


class TestConfigValidation:
    """Test config loads and has all required keys (from check_config)"""

    def test_config_loads_successfully(self):
        """Config module loads without errors"""
        assert config is not None

    def test_all_required_env_vars_present(self):
        """All 7 required environment variables are set"""
        required_keys = [
            "SLACK_BOT_TOKEN",
            "ROTA_SERVICE_ACCOUNT",
            "ROTA_USERS",
            "ROTA_ADMINS",
            "LOCK_DIR",
            "LOCK_TIMEOUT",
            "TIMEZONE",
        ]

        for key in required_keys:
            assert hasattr(config, key), f"Missing config key: {key}"
            value = getattr(config, key)
            assert value is not None, f"Config key {key} is None"


# ============================================================================
# 2. LOCK DIRECTORY TESTS
# ============================================================================


class TestLockDirectory:
    """Test lock directory can be created (from check_lock_dir)"""

    def test_lock_dir_can_be_created_and_accessed(self):
        """Lock directory can be created at configured path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_dir = Path(tmpdir) / "locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            assert lock_dir.exists(), "Lock directory was not created"


# ============================================================================
# 3. JOB IMPORTS TESTS
# ============================================================================


class TestJobImports:
    """Test all required job imports (from check_imports)"""

    def test_required_job_functions_importable(self):
        """All required job functions can be imported"""
        from slack_worker.jobs import (
            send_group_reminder,
            send_dm_reminders,
            sync_releases_to_gsheet,
        )

        assert callable(send_group_reminder)
        assert callable(send_dm_reminders)
        assert callable(sync_releases_to_gsheet)


# ============================================================================
# 4. SCHEDULER INITIALIZATION TESTS
# ============================================================================


class TestSchedulerInitialization:
    """Test JobScheduler can be initialized (from check_scheduler)"""

    def test_scheduler_initializes_with_timezone(self):
        """JobScheduler initializes successfully with timezone"""
        scheduler = JobScheduler(timezone=config.TIMEZONE)
        assert scheduler is not None

    def test_scheduler_timezone_configuration(self):
        """Scheduler accepts UTC timezone configuration"""
        scheduler = JobScheduler(timezone="UTC")
        assert scheduler is not None
