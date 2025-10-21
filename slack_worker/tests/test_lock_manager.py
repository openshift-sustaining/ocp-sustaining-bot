import pytest
import tempfile
import shutil
from pathlib import Path
from filelock import Timeout

from slack_worker.utils.lock_manager import LockManager


class TestLockManager:
    """Test suite for LockManager."""
    
    @pytest.fixture
    def temp_lock_dir(self):
        """Create a temporary directory for lock files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def lock_manager(self, temp_lock_dir):
        """Create a LockManager instance with temp directory."""
        return LockManager(lock_dir=temp_lock_dir)
    
    def test_lock_manager_initialization(self, temp_lock_dir):
        """Test that lock manager initializes correctly."""
        manager = LockManager(lock_dir=temp_lock_dir)
        assert manager.lock_dir == Path(temp_lock_dir)
        assert manager.lock_dir.exists()
    
    def test_acquire_and_release_lock(self, lock_manager):
        """Test basic lock acquisition and release."""
        lock_id = "test_job_1"
        
        with lock_manager.acquire_lock(lock_id, timeout=1):
            # Inside the lock
            assert lock_manager.is_locked(lock_id)
        
        # After exiting context, lock should be released
        assert not lock_manager.is_locked(lock_id)
    
    def test_lock_timeout(self, lock_manager):
        """Test that lock acquisition times out correctly."""
        lock_id = "test_job_2"
        
        # Acquire the lock in one context
        with lock_manager.acquire_lock(lock_id, timeout=1):
            # Try to acquire the same lock in another context (should timeout)
            with pytest.raises(Timeout):
                with lock_manager.acquire_lock(lock_id, timeout=0.5):
                    pass
    
    def test_is_locked(self, lock_manager):
        """Test the is_locked method."""
        lock_id = "test_job_3"
        
        # Initially not locked
        assert not lock_manager.is_locked(lock_id)
        
        # Acquire lock
        with lock_manager.acquire_lock(lock_id, timeout=1):
            # Should be locked now
            assert lock_manager.is_locked(lock_id)
        
        # Should be unlocked again
        assert not lock_manager.is_locked(lock_id)
    
    def test_release_all_locks(self, lock_manager):
        """Test releasing all locks."""
        # Create multiple locks
        locks = ["job_1", "job_2", "job_3"]
        
        # Create lock files manually
        for lock_id in locks:
            lock_file = lock_manager.lock_dir / f"{lock_id}.lock"
            lock_file.touch()
        
        # Release all
        lock_manager.release_all_locks()
        
        # Verify all are gone
        for lock_id in locks:
            lock_file = lock_manager.lock_dir / f"{lock_id}.lock"
            assert not lock_file.exists()
    
    def test_concurrent_lock_access(self, lock_manager):
        """Test that concurrent access is properly prevented."""
        lock_id = "test_concurrent"
        results = []
        
        def try_acquire():
            try:
                with lock_manager.acquire_lock(lock_id, timeout=0.5):
                    results.append("acquired")
            except Timeout:
                results.append("timeout")
        
        # Acquire lock
        with lock_manager.acquire_lock(lock_id, timeout=1):
            # Try to acquire again (should timeout)
            try_acquire()
        
        assert "timeout" in results

