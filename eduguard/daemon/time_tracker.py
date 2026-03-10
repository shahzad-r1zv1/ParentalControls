"""
Time tracker module - monitors active screen time
"""
import psutil
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TimeTracker:
    """Tracks user screen time by monitoring active processes"""

    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.current_session = None
        self.last_check_time = None

    def track_usage(self):
        """Poll system for active user session and record usage"""
        try:
            current_time = datetime.now()
            user_name = self._get_active_user()

            if user_name:
                if self.current_session is None:
                    # Start new session
                    self._start_session(user_name, current_time)
                else:
                    # Update existing session
                    self._update_session(current_time)
            else:
                # No active user, end session if one exists
                if self.current_session is not None:
                    self._end_session(current_time)

            self.last_check_time = current_time
            logger.debug(f"Time tracking check completed at {current_time}")

        except Exception as e:
            logger.error(f"Error in time tracking: {e}", exc_info=True)

    def _get_active_user(self) -> Optional[str]:
        """Get the currently active user"""
        try:
            # Check for active X sessions or Wayland sessions
            users = psutil.users()
            for user in users:
                # Filter for graphical sessions
                if user.terminal and ('tty' in user.terminal or ':' in user.terminal):
                    return user.name
            return None
        except Exception as e:
            logger.error(f"Error getting active user: {e}")
            return None

    def _start_session(self, user_name: str, start_time: datetime):
        """Start a new usage session"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_sessions (start_time, user_name)
                VALUES (?, ?)
            """, (start_time, user_name))
            self.current_session = {
                'id': cursor.lastrowid,
                'user_name': user_name,
                'start_time': start_time
            }
            logger.info(f"Started new session for user {user_name}")

    def _update_session(self, current_time: datetime):
        """Update the current session duration"""
        if self.current_session and self.last_check_time:
            duration = (current_time - self.current_session['start_time']).total_seconds()
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usage_sessions
                    SET duration_seconds = ?
                    WHERE id = ?
                """, (int(duration), self.current_session['id']))

    def _end_session(self, end_time: datetime):
        """End the current usage session"""
        if self.current_session:
            duration = (end_time - self.current_session['start_time']).total_seconds()
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usage_sessions
                    SET end_time = ?, duration_seconds = ?
                    WHERE id = ?
                """, (end_time, int(duration), self.current_session['id']))
            logger.info(f"Ended session {self.current_session['id']} with duration {duration}s")
            self.current_session = None

    def get_today_usage(self, user_name: str) -> int:
        """Get total screen time in seconds for today"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_seconds), 0) as total
                    FROM usage_sessions
                    WHERE user_name = ?
                    AND DATE(start_time) = DATE('now')
                """, (user_name,))
                result = cursor.fetchone()
                return result['total'] if result else 0
        except Exception as e:
            logger.error(f"Error getting today's usage: {e}")
            return 0
