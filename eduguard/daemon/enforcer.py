"""
Enforcer module - enforces screen time limits
"""
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Enforcer:
    """Enforces screen time limits by locking sessions"""

    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.locked_users = set()

    def check_and_enforce(self, time_tracker):
        """Check limits and enforce if necessary"""
        try:
            # Get active user from time tracker
            user_name = time_tracker._get_active_user()
            if not user_name:
                return

            # Get today's usage
            usage_seconds = time_tracker.get_today_usage(user_name)
            limit_seconds = self.config['limits']['daily_screen_time'] * 60

            logger.debug(f"User {user_name}: {usage_seconds}s used, {limit_seconds}s limit")

            # Check if limit exceeded
            if usage_seconds >= limit_seconds and user_name not in self.locked_users:
                self._lock_session(user_name)
                self.locked_users.add(user_name)
                logger.info(f"Locked session for user {user_name} - limit exceeded")

        except Exception as e:
            logger.error(f"Error in enforcer: {e}", exc_info=True)

    def _lock_session(self, user_name: str):
        """Lock the user's session using loginctl"""
        try:
            # Get the session ID for the user
            result = subprocess.run(
                ['loginctl', 'list-sessions', '--no-legend'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] == user_name:
                        session_id = parts[0]
                        # Lock the session
                        subprocess.run(
                            ['loginctl', 'lock-session', session_id],
                            timeout=5,
                            check=True
                        )
                        logger.info(f"Locked session {session_id} for user {user_name}")
                        return

            logger.warning(f"Could not find session for user {user_name}")

        except subprocess.TimeoutExpired:
            logger.error("Timeout while trying to lock session")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error locking session: {e}")
        except Exception as e:
            logger.error(f"Unexpected error locking session: {e}", exc_info=True)

    def reset_daily_locks(self):
        """Reset locked users at start of new day"""
        self.locked_users.clear()
        logger.info("Daily lock status reset")
