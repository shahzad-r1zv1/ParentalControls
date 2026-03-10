"""
Integration tests for Flask dashboard - simplified
"""
import pytest
import tempfile
import os
from flask import Flask
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestDashboardSimplified:
    """Test Flask dashboard routes (simplified without full app load)"""

    def test_database_integration_with_dashboard_queries(self, temp_db):
        """Test dashboard queries work with database"""
        # Insert test data
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            # Insert usage session
            cursor.execute("""
                INSERT INTO usage_sessions (start_time, duration_seconds, user_name)
                VALUES (datetime('now'), 3600, 'testuser')
            """)

            # Insert browser visits
            cursor.execute("""
                INSERT INTO browser_visits (url, title, visit_time, user_name, visit_count)
                VALUES ('https://example.com', 'Example', datetime('now'), 'testuser', 1)
            """)

            # Insert blocked attempts
            cursor.execute("""
                INSERT INTO blocked_attempts (domain, reason, user_name)
                VALUES ('bad-site.com', 'Static blocklist', 'testuser')
            """)

            # Insert AI insights
            cursor.execute("""
                INSERT INTO ai_insights (insight_type, content, summary)
                VALUES ('daily_summary', 'Activity data', 'Test insight')
            """)

        # Test queries that dashboard would use
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            # Dashboard query: screen time today
            cursor.execute("""
                SELECT COALESCE(SUM(duration_seconds), 0) as total
                FROM usage_sessions
                WHERE DATE(start_time) = DATE('now')
            """)
            screen_time = cursor.fetchone()['total']
            assert screen_time == 3600

            # Dashboard query: blocked attempts today
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM blocked_attempts
                WHERE DATE(timestamp) = DATE('now')
            """)
            blocked_count = cursor.fetchone()['count']
            assert blocked_count == 1

            # Dashboard query: top sites
            cursor.execute("""
                SELECT url, COUNT(*) as visits
                FROM browser_visits
                WHERE DATE(visit_time) = DATE('now')
                GROUP BY url
                ORDER BY visits DESC
                LIMIT 10
            """)
            top_sites = cursor.fetchall()
            assert len(top_sites) == 1
            assert top_sites[0]['url'] == 'https://example.com'

            # Dashboard query: latest insight
            cursor.execute("""
                SELECT summary, generated_at
                FROM ai_insights
                ORDER BY generated_at DESC
                LIMIT 1
            """)
            insight = cursor.fetchone()
            assert insight is not None
            assert insight['summary'] == 'Test insight'

    def test_history_query_integration(self, temp_db):
        """Test history page queries"""
        # Insert history data for different days
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO browser_visits (url, title, visit_time, user_name, visit_count)
                VALUES
                ('https://site1.com', 'Site 1', datetime('now', '-1 day'), 'testuser', 1),
                ('https://site2.com', 'Site 2', datetime('now', '-2 days'), 'testuser', 2),
                ('https://site3.com', 'Site 3', datetime('now', '-8 days'), 'testuser', 1)
            """)

        # Test 7-day history query
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, title, visit_time, visit_count
                FROM browser_visits
                WHERE visit_time >= datetime('now', '-7 days')
                ORDER BY visit_time DESC
            """)
            results = cursor.fetchall()
            assert len(results) == 2  # Only 2 within last 7 days

        # Test 30-day history query
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, title, visit_time, visit_count
                FROM browser_visits
                WHERE visit_time >= datetime('now', '-30 days')
                ORDER BY visit_time DESC
            """)
            results = cursor.fetchall()
            assert len(results) == 3  # All 3 within last 30 days

    def test_reports_query_integration(self, temp_db):
        """Test reports page queries"""
        # Insert usage data for multiple days
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_sessions (start_time, duration_seconds, user_name)
                VALUES
                (datetime('now'), 3600, 'testuser'),
                (datetime('now', '-1 day'), 7200, 'testuser'),
                (datetime('now', '-2 days'), 1800, 'testuser')
            """)

        # Test daily usage query for last 7 days
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    DATE(start_time) as date,
                    SUM(duration_seconds) / 60 as minutes
                FROM usage_sessions
                WHERE start_time >= datetime('now', '-7 days')
                GROUP BY DATE(start_time)
                ORDER BY date
            """)
            daily_usage = cursor.fetchall()
            assert len(daily_usage) >= 1
            assert all(row['minutes'] > 0 for row in daily_usage)

    def test_config_audit_integration(self, temp_db):
        """Test config audit logging"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO config_audit (changed_by, changes)
                VALUES ('parent', 'Updated daily limit to 120 minutes')
            """)

        # Verify audit log
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT changed_by, changes FROM config_audit
                ORDER BY timestamp DESC LIMIT 1
            """)
            audit = cursor.fetchone()
            assert audit is not None
            assert audit['changed_by'] == 'parent'
            assert '120 minutes' in audit['changes']

    def test_job_runs_tracking(self, temp_db):
        """Test job execution tracking"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            # Log job start
            cursor.execute("""
                INSERT INTO job_runs (job_name, status)
                VALUES ('time_tracking', 'started')
            """)
            job_id = cursor.lastrowid

            # Log job completion
            cursor.execute("""
                UPDATE job_runs
                SET status = 'completed', completed_at = datetime('now')
                WHERE id = ?
            """, (job_id,))

        # Verify job tracking
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM job_runs WHERE id = ?
            """, (job_id,))
            job = cursor.fetchone()
            assert job['status'] == 'completed'
            assert job['completed_at'] is not None
