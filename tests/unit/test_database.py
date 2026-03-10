"""
Unit tests for Database module
"""
import pytest
import sqlite3
import tempfile
import os
from eduguard.daemon.database import Database


@pytest.mark.unit
class TestDatabase:
    """Test Database class functionality"""

    def test_database_initialization(self, temp_db):
        """Test database is properly initialized"""
        assert temp_db.db_path is not None
        assert os.path.exists(temp_db.db_path)

    def test_database_schema_created(self, temp_db):
        """Test all required tables are created"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            # Check all tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
            """)
            tables = [row['name'] for row in cursor.fetchall()]

            expected_tables = [
                'usage_sessions',
                'browser_visits',
                'blocked_attempts',
                'ai_decisions',
                'app_usage',
                'ai_insights',
                'config_audit',
                'job_runs',
                'browser_history_cursor'
            ]

            for table in expected_tables:
                assert table in tables, f"Table {table} not found"

    def test_wal_mode_enabled(self, temp_db):
        """Test WAL mode is enabled"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            result = cursor.fetchone()
            assert result[0].lower() == 'wal'

    def test_insert_usage_session(self, temp_db):
        """Test inserting a usage session"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_sessions (start_time, user_name)
                VALUES (datetime('now'), 'testuser')
            """)
            session_id = cursor.lastrowid

        # Verify insertion
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM usage_sessions WHERE id = ?
            """, (session_id,))
            session = cursor.fetchone()

            assert session is not None
            assert session['user_name'] == 'testuser'

    def test_insert_browser_visit(self, temp_db):
        """Test inserting a browser visit"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO browser_visits (url, title, visit_time, user_name)
                VALUES (?, ?, datetime('now'), ?)
            """, ('https://example.com', 'Example Site', 'testuser'))

        # Verify insertion
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM browser_visits WHERE url = ?
            """, ('https://example.com',))
            visit = cursor.fetchone()

            assert visit is not None
            assert visit['title'] == 'Example Site'

    def test_insert_blocked_attempt(self, temp_db):
        """Test inserting a blocked attempt"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO blocked_attempts (domain, reason, user_name)
                VALUES (?, ?, ?)
            """, ('bad-site.com', 'Static blocklist', 'testuser'))

        # Verify insertion
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM blocked_attempts WHERE domain = ?
            """, ('bad-site.com',))
            attempt = cursor.fetchone()

            assert attempt is not None
            assert attempt['reason'] == 'Static blocklist'

    def test_ai_decision_cache(self, temp_db):
        """Test AI decision caching"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions (domain, decision, reason, confidence)
                VALUES (?, ?, ?, ?)
            """, ('example.com', 'allow', 'Educational content', 0.95))

        # Verify and retrieve
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ai_decisions WHERE domain = ?
            """, ('example.com',))
            decision = cursor.fetchone()

            assert decision is not None
            assert decision['decision'] == 'allow'
            assert decision['confidence'] == 0.95

    def test_transaction_rollback(self, temp_db):
        """Test transaction rollback on error"""
        try:
            with temp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO usage_sessions (start_time, user_name)
                    VALUES (datetime('now'), 'testuser')
                """)
                # Trigger an error
                cursor.execute("INSERT INTO nonexistent_table VALUES (1)")
        except Exception:
            pass

        # Check that the rollback happened
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM usage_sessions")
            count = cursor.fetchone()['count']
            # Should be 0 because transaction rolled back
            assert count == 0

    def test_indices_created(self, temp_db):
        """Test that performance indices are created"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND sql IS NOT NULL
            """)
            indices = [row['name'] for row in cursor.fetchall()]

            expected_indices = [
                'idx_usage_sessions_user',
                'idx_browser_visits_user',
                'idx_blocked_attempts_timestamp',
                'idx_ai_decisions_domain'
            ]

            for index in expected_indices:
                assert index in indices, f"Index {index} not found"
