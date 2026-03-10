"""
Unit tests for Enforcer module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from eduguard.daemon.enforcer import Enforcer
from eduguard.daemon.time_tracker import TimeTracker


@pytest.mark.unit
class TestEnforcer:
    """Test Enforcer class functionality"""

    @pytest.fixture
    def enforcer(self, temp_db, test_config):
        """Create an Enforcer instance for testing"""
        return Enforcer(temp_db, test_config)

    @pytest.fixture
    def time_tracker(self, temp_db, test_config):
        """Create a TimeTracker instance for testing"""
        return TimeTracker(temp_db, test_config)

    def test_initialization(self, enforcer):
        """Test Enforcer initialization"""
        assert enforcer.db is not None
        assert enforcer.config is not None
        assert enforcer.locked_users == set()

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_check_and_enforce_under_limit(self, mock_run, enforcer, time_tracker):
        """Test enforcement when under limit"""
        # Mock active user
        with patch.object(time_tracker, '_get_active_user', return_value='testuser'):
            with patch.object(time_tracker, 'get_today_usage', return_value=3600):  # 1 hour
                enforcer.check_and_enforce(time_tracker)

        # Should not lock (limit is 2 hours = 7200 seconds)
        mock_run.assert_not_called()
        assert 'testuser' not in enforcer.locked_users

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_check_and_enforce_over_limit(self, mock_run, enforcer, time_tracker):
        """Test enforcement when over limit"""
        # Mock subprocess.run for list-sessions
        list_result = Mock()
        list_result.returncode = 0
        list_result.stdout = "1    seat0    testuser\n"

        # Mock subprocess.run for lock-session
        lock_result = Mock()
        lock_result.returncode = 0

        mock_run.side_effect = [list_result, lock_result]

        # Mock active user with usage over limit
        with patch.object(time_tracker, '_get_active_user', return_value='testuser'):
            with patch.object(time_tracker, 'get_today_usage', return_value=7200):  # 2 hours (at limit)
                enforcer.check_and_enforce(time_tracker)

        # Should attempt to lock session
        assert mock_run.call_count >= 1
        assert 'testuser' in enforcer.locked_users

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_check_and_enforce_already_locked(self, mock_run, enforcer, time_tracker):
        """Test enforcement doesn't re-lock already locked user"""
        # Mark user as already locked
        enforcer.locked_users.add('testuser')

        with patch.object(time_tracker, '_get_active_user', return_value='testuser'):
            with patch.object(time_tracker, 'get_today_usage', return_value=7200):
                enforcer.check_and_enforce(time_tracker)

        # Should not attempt to lock again
        mock_run.assert_not_called()

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_lock_session_success(self, mock_run, enforcer):
        """Test successful session locking"""
        # Mock subprocess.run for list-sessions
        list_result = Mock()
        list_result.returncode = 0
        list_result.stdout = "1    seat0    testuser\n2    seat0    otheruser\n"

        # Mock subprocess.run for lock-session
        lock_result = Mock()
        lock_result.returncode = 0

        mock_run.side_effect = [list_result, lock_result]

        enforcer._lock_session('testuser')

        # Verify commands called
        assert mock_run.call_count == 2
        # Check lock-session was called with correct session ID
        lock_call = mock_run.call_args_list[1]
        assert 'loginctl' in lock_call[0][0]
        assert 'lock-session' in lock_call[0][0]
        assert '1' in lock_call[0][0]

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_lock_session_user_not_found(self, mock_run, enforcer):
        """Test locking when user session not found"""
        # Mock subprocess.run for list-sessions
        list_result = Mock()
        list_result.returncode = 0
        list_result.stdout = "1    seat0    otheruser\n"

        mock_run.return_value = list_result

        # Should not raise exception
        enforcer._lock_session('testuser')

        # Only list-sessions should be called
        assert mock_run.call_count == 1

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_lock_session_timeout(self, mock_run, enforcer):
        """Test handling of timeout during session locking"""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired('loginctl', 5)

        # Should not raise exception
        enforcer._lock_session('testuser')

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_lock_session_error(self, mock_run, enforcer):
        """Test handling of error during session locking"""
        from subprocess import CalledProcessError

        list_result = Mock()
        list_result.returncode = 0
        list_result.stdout = "1    seat0    testuser\n"

        mock_run.side_effect = [list_result, CalledProcessError(1, 'loginctl')]

        # Should not raise exception
        enforcer._lock_session('testuser')

    def test_reset_daily_locks(self, enforcer):
        """Test resetting locked users"""
        enforcer.locked_users = {'user1', 'user2', 'user3'}

        enforcer.reset_daily_locks()

        assert len(enforcer.locked_users) == 0

    def test_check_and_enforce_no_active_user(self, enforcer, time_tracker):
        """Test enforcement when no active user"""
        with patch.object(time_tracker, '_get_active_user', return_value=None):
            # Should not raise exception
            enforcer.check_and_enforce(time_tracker)

    @patch('eduguard.daemon.enforcer.subprocess.run')
    def test_check_and_enforce_with_exception(self, mock_run, enforcer, time_tracker):
        """Test error handling in check_and_enforce"""
        with patch.object(time_tracker, '_get_active_user', side_effect=Exception("Test error")):
            # Should not raise exception
            enforcer.check_and_enforce(time_tracker)
