"""
Browser monitor module - monitors Firefox browsing history
"""
import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class BrowserMonitor:
    """Monitors Firefox browser history"""

    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.temp_db_path = "/tmp/eduguard_places.sqlite"

    def check_browser_history(self):
        """Check Firefox history and log visits"""
        try:
            # Find Firefox profile
            firefox_profile = self._find_firefox_profile()
            if not firefox_profile:
                logger.warning("Firefox profile not found")
                return

            places_db = firefox_profile / "places.sqlite"
            if not places_db.exists():
                logger.warning(f"places.sqlite not found at {places_db}")
                return

            # Copy to temp location to avoid lock conflicts
            try:
                shutil.copy2(places_db, self.temp_db_path)
            except Exception as e:
                logger.error(f"Failed to copy places.sqlite: {e}")
                return

            # Read history
            visits = self._read_history()
            if visits:
                self._save_visits(visits)
                logger.info(f"Processed {len(visits)} browser visits")

        except Exception as e:
            logger.error(f"Error checking browser history: {e}", exc_info=True)
        finally:
            # Clean up temp file
            try:
                if Path(self.temp_db_path).exists():
                    Path(self.temp_db_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp database: {e}")

    def _find_firefox_profile(self) -> Optional[Path]:
        """Find the Firefox profile directory"""
        try:
            # Common Firefox profile locations
            firefox_base = Path.home() / ".mozilla" / "firefox"
            if not firefox_base.exists():
                return None

            # Look for default profile or first available profile
            for profile_dir in firefox_base.iterdir():
                if profile_dir.is_dir() and (profile_dir / "places.sqlite").exists():
                    return profile_dir

            return None
        except Exception as e:
            logger.error(f"Error finding Firefox profile: {e}")
            return None

    def _read_history(self) -> List[Dict]:
        """Read history from copied places.sqlite"""
        visits = []
        try:
            # Get last processed visit date
            last_visit_date = self._get_last_cursor()

            conn = sqlite3.connect(self.temp_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query for new visits
            cursor.execute("""
                SELECT
                    moz_places.url,
                    moz_places.title,
                    moz_historyvisits.visit_date,
                    COUNT(*) as visit_count
                FROM moz_historyvisits
                JOIN moz_places ON moz_historyvisits.place_id = moz_places.id
                WHERE moz_historyvisits.visit_date > ?
                GROUP BY moz_places.url, moz_places.title, moz_historyvisits.visit_date
                ORDER BY moz_historyvisits.visit_date
            """, (last_visit_date,))

            for row in cursor.fetchall():
                visits.append({
                    'url': row['url'],
                    'title': row['title'],
                    'visit_date': row['visit_date'],
                    'visit_count': row['visit_count']
                })

            conn.close()

            # Update cursor if we got new visits
            if visits:
                max_visit_date = max(v['visit_date'] for v in visits)
                self._update_cursor(max_visit_date)

        except Exception as e:
            logger.error(f"Error reading browser history: {e}", exc_info=True)

        return visits

    def _get_last_cursor(self) -> int:
        """Get the last processed visit date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT last_visit_date FROM browser_history_cursor WHERE id = 1")
                result = cursor.fetchone()
                return result['last_visit_date'] if result else 0
        except Exception as e:
            logger.error(f"Error getting cursor: {e}")
            return 0

    def _update_cursor(self, visit_date: int):
        """Update the last processed visit date"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO browser_history_cursor (id, last_visit_date)
                    VALUES (1, ?)
                """, (visit_date,))
        except Exception as e:
            logger.error(f"Error updating cursor: {e}")

    def _save_visits(self, visits: List[Dict]):
        """Save visits to database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                for visit in visits:
                    # Convert Firefox timestamp (microseconds) to datetime
                    visit_time = datetime.fromtimestamp(visit['visit_date'] / 1000000)
                    cursor.execute("""
                        INSERT INTO browser_visits (url, title, visit_time, visit_count, user_name)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        visit['url'],
                        visit['title'],
                        visit_time,
                        visit['visit_count'],
                        'child'  # Default user - could be enhanced to track actual user
                    ))
        except Exception as e:
            logger.error(f"Error saving visits: {e}", exc_info=True)
