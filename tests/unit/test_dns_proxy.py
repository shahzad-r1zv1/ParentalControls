"""
Unit tests for DNSProxy module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path
from eduguard.daemon.dns_proxy import DNSProxy


@pytest.mark.unit
class TestDNSProxy:
    """Test DNSProxy class functionality"""

    @pytest.fixture
    def dns_proxy(self, temp_db, test_config, temp_blocklist):
        """Create a DNSProxy instance for testing"""
        test_config['dns']['blocklist_path'] = temp_blocklist
        return DNSProxy(temp_db, test_config)

    def test_initialization(self, dns_proxy):
        """Test DNSProxy initialization"""
        assert dns_proxy.db is not None
        assert dns_proxy.config is not None
        assert len(dns_proxy.blocked_domains) > 0

    def test_load_blocklist(self, dns_proxy):
        """Test loading blocklist from file"""
        # Check that domains from temp_blocklist are loaded
        assert 'example-bad.com' in dns_proxy.blocked_domains
        assert 'test-blocked.org' in dns_proxy.blocked_domains
        assert 'adult-content.net' in dns_proxy.blocked_domains

    def test_check_domain_in_static_blocklist(self, dns_proxy):
        """Test checking domain in static blocklist"""
        result = dns_proxy.check_domain('example-bad.com')
        assert result is True

        # Verify blocked attempt logged
        with dns_proxy.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM blocked_attempts WHERE domain = ?
            """, ('example-bad.com',))
            attempt = cursor.fetchone()
            assert attempt is not None
            assert 'Static blocklist' in attempt['reason']

    def test_check_domain_not_in_blocklist(self, dns_proxy):
        """Test checking domain not in blocklist"""
        result = dns_proxy.check_domain('safe-site.com')
        assert result is False

    def test_check_domain_with_ai_decision(self, dns_proxy):
        """Test checking domain with AI decision"""
        # Add AI decision to cache
        with dns_proxy.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions (domain, decision, reason, confidence)
                VALUES (?, ?, ?, ?)
            """, ('ai-blocked.com', 'block', 'AI classified as inappropriate', 0.92))

        result = dns_proxy.check_domain('ai-blocked.com')
        assert result is True

    def test_get_ai_blocked_domains(self, dns_proxy):
        """Test getting AI-blocked domains"""
        # Add multiple AI decisions
        with dns_proxy.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions (domain, decision, reason, confidence)
                VALUES
                (?, ?, ?, ?),
                (?, ?, ?, ?),
                (?, ?, ?, ?)
            """, ('blocked1.com', 'block', 'Reason 1', 0.9,
                  'allowed.com', 'allow', 'Reason 2', 0.8,
                  'blocked2.com', 'block', 'Reason 3', 0.95))

        blocked = dns_proxy._get_ai_blocked_domains()
        assert 'blocked1.com' in blocked
        assert 'blocked2.com' in blocked
        assert 'allowed.com' not in blocked

    @patch('eduguard.daemon.dns_proxy.subprocess.run')
    @patch('eduguard.daemon.dns_proxy.Path.write_text')
    def test_update_dnsmasq_config(self, mock_write, mock_run, dns_proxy):
        """Test updating dnsmasq configuration"""
        # Add some AI blocked domains
        with dns_proxy.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions (domain, decision, reason, confidence)
                VALUES (?, ?, ?, ?)
            """, ('ai-blocked.com', 'block', 'AI decision', 0.9))

        dns_proxy.update_dnsmasq_config()

        # Verify config file write attempted
        assert mock_write.called or mock_run.called

    @patch('eduguard.daemon.dns_proxy.subprocess.run')
    def test_reload_dnsmasq_success(self, mock_run, dns_proxy):
        """Test successful dnsmasq reload"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        dns_proxy._reload_dnsmasq()

        mock_run.assert_called_once()
        assert 'systemctl' in mock_run.call_args[0][0]
        assert 'reload' in mock_run.call_args[0][0]
        assert 'dnsmasq' in mock_run.call_args[0][0]

    @patch('eduguard.daemon.dns_proxy.subprocess.run')
    def test_reload_dnsmasq_timeout(self, mock_run, dns_proxy):
        """Test handling dnsmasq reload timeout"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('systemctl', 10)

        # Should not raise exception
        dns_proxy._reload_dnsmasq()

    def test_log_blocked_attempt(self, dns_proxy):
        """Test logging blocked attempts"""
        dns_proxy._log_blocked_attempt('blocked-site.com', 'Test reason')

        with dns_proxy.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM blocked_attempts WHERE domain = ?
            """, ('blocked-site.com',))
            attempt = cursor.fetchone()
            assert attempt is not None
            assert attempt['reason'] == 'Test reason'
