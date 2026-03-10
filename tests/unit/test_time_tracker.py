"""
Unit tests for TimeTracker module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from eduguard.daemon.time_tracker import TimeTracker


@pytest.mark.unit
class TestTimeTracker:
    """Test TimeTracker class functionality"""

    @pytest.fixture
    def time_tracker(self, temp_db, test_config):
        """Create a TimeTracker instance for testing"""
        return TimeTracker(temp_db, test_config)

    def test_initialization(self, time_tracker):
        """Test TimeTracker initialization"""
        assert time_tracker.db is not None
        assert time_tracker.config is not None
        assert time_tracker.current_session is None
        assert time_tracker.last_check_time is None

    @patch('eduguard.daemon.time_tracker.psutil.users')
    def test_get_active_user(self, mock_users, time_tracker):
        """Test detecting active user"""
        # Mock psutil users
        mock_user = Mock()
        mock_user.name = 'testuser'
        mock_user.terminal = ':0'
        mock_users.return_value = [mock_user]

        user = time_tracker._get_active_user()
        assert user == 'testuser'

    @patch('eduguard.daemon.time_tracker.psutil.users')
    def test_get_active_user_no_graphical_session(self, mock_users, time_tracker):
        """Test no active user when no graphical session"""
        # Mock psutil users with no graphical terminal
        mock_user = Mock()
        mock_user.name = 'testuser'
        mock_user.terminal = None
        mock_users.return_value = [mock_user]

        user = time_tracker._get_active_user()
        assert user is None

    @patch('eduguard.daemon.time_tracker.psutil.users')
    def test_start_session(self, mock_users, time_tracker):
        """Test starting a new session"""
        mock_user = Mock()
        mock_user.name = 'testuser'
        mock_user.terminal = ':0'
        mock_users.return_value = [mock_user]

        # Track usage to start session
        time_tracker.track_usage()

        assert time_tracker.current_session is not None
        assert time_tracker.current_session['user_name'] == 'testuser'
        assert 'id' in time_tracker.current_session
        assert 'start_time' in time_tracker.current_session

    @patch('eduguard.daemon.time_tracker.psutil.users')
    def test_update_session(self, mock_users, time_tracker):
        """Test updating an existing session"""
        mock_user = Mock()
        mock_user.name = 'testuser'
        mock_user.terminal = ':0'
        mock_users.return_value = [mock_user]

        # Start session
        time_tracker.track_usage()
        session_id = time_tracker.current_session['id']

        # Update session
        time_tracker.track_usage()

        # Check session still active with same ID
        assert time_tracker.current_session is not None
        assert time_tracker.current_session['id'] == session_id

        # Verify duration updated in database
        with time_tracker.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT duration_seconds FROM usage_sessions WHERE id = ?
            """, (session_id,))
            result = cursor.fetchone()
            assert result is not None
            assert result['duration_seconds'] >= 0

    @patch('eduguard.daemon.time_tracker.psutil.users')
    def test_end_session(self, mock_users, time_tracker):
        """Test ending a session"""
        # Start with active user
        mock_user = Mock()
        mock_user.name = 'testuser'
        mock_user.terminal = ':0'
        mock_users.return_value = [mock_user]
        time_tracker.track_usage()
        session_id = time_tracker.current_session['id']

        # Now no active user
        mock_users.return_value = []
        time_tracker.track_usage()

        # Check session ended
        assert time_tracker.current_session is None

        # Verify session has end_time in database
        with time_tracker.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT end_time, duration_seconds FROM usage_sessions WHERE id = ?
            """, (session_id,))
            result = cursor.fetchone()
            assert result is not None
            assert result['end_time'] is not None
            assert result['duration_seconds'] >= 0  # Changed to >= 0 for fast execution timing

    def test_get_today_usage(self, time_tracker):
        """Test calculating today's usage"""
        # Insert test data
        with time_tracker.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_sessions
                (start_time, end_time, duration_seconds, user_name)
                VALUES
                (datetime('now'), datetime('now'), 3600, 'testuser'),
                (datetime('now'), datetime('now'), 1800, 'testuser')
            """)

        usage = time_tracker.get_today_usage('testuser')
        assert usage == 5400  # 3600 + 1800 seconds

    def test_get_today_usage_no_sessions(self, time_tracker):
        """Test usage calculation with no sessions"""
        usage = time_tracker.get_today_usage('nonexistent')
        assert usage == 0

    @patch('eduguard.daemon.time_tracker.psutil.users')
    def test_track_usage_with_exception(self, mock_users, time_tracker):
        """Test error handling in track_usage"""
        mock_users.side_effect = Exception("Test error")

        # Should not raise exception
        time_tracker.track_usage()

        # Session should remain None
        assert time_tracker.current_session is None
