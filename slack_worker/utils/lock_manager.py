"""
Lock Manager
============
Provides distributed locking mechanism for horizontal scaling.

This ensures that scheduled jobs don't execute multiple times when
the service is scaled across multiple pods/containers in K8s/OCP.

Uses file-based locking with a shared PVC in K8s/OCP environments.
"""

import logging
import os
from pathlib import Path
from filelock import FileLock, Timeout
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class LockManager:
    """
    Manages file-based locks for distributed job coordination.
    
    In a scaled environment (multiple pods), this prevents the same
    job from running simultaneously on different instances.
    
    Usage:
        lock_manager = LockManager("/path/to/shared/locks")
        
        with lock_manager.acquire_lock("my_job_id", timeout=10):
            # Execute job logic
            pass
    """
    
    def __init__(self, lock_dir: str = "/tmp/slack_worker_locks"):
        """
        Initialize the lock manager.
        
        Args:
            lock_dir: Directory to store lock files (should be on shared PVC in K8s)
        """
        self.lock_dir = Path(lock_dir)
        self._ensure_lock_directory()
    
    def _ensure_lock_directory(self):
        """Create the lock directory if it doesn't exist."""
        try:
            self.lock_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Lock directory: {self.lock_dir}")
        except Exception as e:
            logger.error(f"Failed to create lock directory: {e}")
            raise
    
    @contextmanager
    def acquire_lock(self, lock_id: str, timeout: int = 10):
        """
        Acquire a lock for the given job ID.
        
        This is a context manager that automatically releases the lock
        when the block completes or if an error occurs.
        
        Args:
            lock_id: Unique identifier for the lock
            timeout: Maximum time to wait for lock acquisition (seconds)
            
        Yields:
            FileLock: The acquired lock object
            
        Raises:
            Timeout: If lock cannot be acquired within timeout period
            
        Example:
            with lock_manager.acquire_lock("rota_reminder_2024-01-15", timeout=5):
                # Execute job
                send_reminders()
        """
        lock_file = self.lock_dir / f"{lock_id}.lock"
        lock = FileLock(str(lock_file), timeout=timeout)
        
        try:
            logger.debug(f"Attempting to acquire lock: {lock_id}")
            with lock.acquire(timeout=timeout):
                logger.info(f"Lock acquired: {lock_id}")
                yield lock
        except Timeout:
            logger.warning(
                f"Could not acquire lock '{lock_id}' within {timeout}s - "
                f"job likely running on another instance"
            )
            raise
        finally:
            # Clean up lock file if possible (best effort)
            try:
                if lock_file.exists():
                    lock_file.unlink()
                    logger.debug(f"Cleaned up lock file: {lock_id}")
            except Exception as e:
                logger.debug(f"Could not clean up lock file: {e}")
    
    def is_locked(self, lock_id: str) -> bool:
        """
        Check if a lock is currently held.
        
        Args:
            lock_id: Unique identifier for the lock
            
        Returns:
            bool: True if locked, False otherwise
        """
        lock_file = self.lock_dir / f"{lock_id}.lock"
        lock = FileLock(str(lock_file))
        
        try:
            with lock.acquire(timeout=0.1):
                return False
        except Timeout:
            return True
    
    def release_all_locks(self):
        """
        Release all locks (cleanup utility).
        
        This should typically only be called during shutdown or maintenance.
        """
        try:
            for lock_file in self.lock_dir.glob("*.lock"):
                lock_file.unlink()
                logger.info(f"Released lock: {lock_file.name}")
        except Exception as e:
            logger.error(f"Error releasing locks: {e}")

