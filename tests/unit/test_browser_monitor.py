"""
Unit tests for BrowserMonitor module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path
from eduguard.daemon.browser_monitor import BrowserMonitor


@pytest.mark.unit
class TestBrowserMonitor:
    """Test BrowserMonitor class functionality"""

    @pytest.fixture
    def browser_monitor(self, temp_db, test_config):
        """Create a BrowserMonitor instance for testing"""
        return BrowserMonitor(temp_db, test_config)

    def test_initialization(self, browser_monitor):
        """Test BrowserMonitor initialization"""
        assert browser_monitor.db is not None
        assert browser_monitor.config is not None
        assert browser_monitor.temp_db_path == "/tmp/eduguard_places.sqlite"

    @patch('eduguard.daemon.browser_monitor.Path.exists')
    def test_find_firefox_profile_not_found(self, mock_exists, browser_monitor):
        """Test when Firefox profile not found"""
        mock_exists.return_value = False

        profile = browser_monitor._find_firefox_profile()
        assert profile is None

    @patch('eduguard.daemon.browser_monitor.Path.iterdir')
    @patch('eduguard.daemon.browser_monitor.Path.exists')
    @patch('eduguard.daemon.browser_monitor.Path.home')
    def test_find_firefox_profile_found(self, mock_home, mock_exists, mock_iterdir, browser_monitor):
        """Test finding Firefox profile"""
        # Mock home directory
        mock_home.return_value = Path('/home/testuser')

        # Mock profile directory structure
        mock_profile = Mock()
        mock_profile.is_dir.return_value = True
        mock_profile.__truediv__ = lambda self, x: Path('/home/testuser/.mozilla/firefox/profile.default/places.sqlite')

        mock_iterdir.return_value = [mock_profile]
        mock_exists.return_value = True

        profile = browser_monitor._find_firefox_profile()
        assert profile is not None

    def test_get_last_cursor(self, browser_monitor):
        """Test getting last cursor value"""
        # Initialize with no cursor
        cursor = browser_monitor._get_last_cursor()
        assert cursor == 0

        # Set a cursor value
        with browser_monitor.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO browser_history_cursor (id, last_visit_date)
                VALUES (1, 12345678)
            """)

        cursor = browser_monitor._get_last_cursor()
        assert cursor == 12345678

    def test_update_cursor(self, browser_monitor):
        """Test updating cursor value"""
        browser_monitor._update_cursor(98765432)

        with browser_monitor.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_visit_date FROM browser_history_cursor WHERE id = 1")
            result = cursor.fetchone()
            assert result['last_visit_date'] == 98765432

    def test_save_visits(self, browser_monitor):
        """Test saving browser visits"""
        visits = [
            {
                'url': 'https://example.com',
                'title': 'Example Site',
                'visit_date': 1709654400000000,  # Microseconds
                'visit_count': 1
            },
            {
                'url': 'https://test.org',
                'title': 'Test Site',
                'visit_date': 1709654500000000,
                'visit_count': 2
            }
        ]

        browser_monitor._save_visits(visits)

        # Verify visits saved
        with browser_monitor.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM browser_visits")
            count = cursor.fetchone()['count']
            assert count == 2

            cursor.execute("SELECT * FROM browser_visits WHERE url = ?", ('https://example.com',))
            visit = cursor.fetchone()
            assert visit is not None
            assert visit['title'] == 'Example Site'

    @patch('eduguard.daemon.browser_monitor.Path.exists')
    @patch('eduguard.daemon.browser_monitor.shutil.copy2')
    def test_check_browser_history_no_profile(self, mock_copy, mock_exists, browser_monitor):
        """Test checking history when no profile found"""
        with patch.object(browser_monitor, '_find_firefox_profile', return_value=None):
            browser_monitor.check_browser_history()

        # Should not attempt to copy
        mock_copy.assert_not_called()

    @patch('eduguard.daemon.browser_monitor.Path.unlink')
    @patch('eduguard.daemon.browser_monitor.Path.exists')
    @patch('eduguard.daemon.browser_monitor.shutil.copy2')
    def test_check_browser_history_copy_error(self, mock_copy, mock_exists, mock_unlink, browser_monitor):
        """Test handling copy error"""
        mock_profile = Path('/home/testuser/.mozilla/firefox/profile.default')
        mock_copy.side_effect = Exception("Copy failed")
        mock_exists.return_value = True

        with patch.object(browser_monitor, '_find_firefox_profile', return_value=mock_profile):
            browser_monitor.check_browser_history()

        # Should handle exception gracefully
        mock_copy.assert_called_once()
