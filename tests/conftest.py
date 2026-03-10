"""
Pytest fixtures and configuration for EduGuard tests
"""
import pytest
import tempfile
import os
from pathlib import Path
from eduguard.daemon.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary test database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
        # Also cleanup WAL files
        for suffix in ['-wal', '-shm']:
            wal_file = db_path + suffix
            if os.path.exists(wal_file):
                os.unlink(wal_file)
    except Exception:
        pass


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        'database': {
            'path': '/tmp/test_eduguard.db'
        },
        'limits': {
            'daily_screen_time': 120  # 2 hours
        },
        'browser': {
            'firefox_profile_path': '~/.mozilla/firefox',
            'check_interval': 300
        },
        'dns': {
            'port': 53,
            'blocklist_path': '/tmp/test_blocklist.txt',
            'dnsmasq_config': '/tmp/test_eduguard.conf'
        },
        'ai': {
            'model': 'llama3.2:3b',
            'ollama_host': 'http://localhost:11434',
            'batch_interval': 86400,
            'confidence_threshold': 0.7
        },
        'tracking': {
            'poll_interval': 60
        },
        'dashboard': {
            'host': '127.0.0.1',
            'port': 5000,
            'secret_key': 'test-secret-key'
        },
        'logging': {
            'level': 'INFO',
            'file': '/tmp/test_eduguard.log'
        }
    }


@pytest.fixture
def temp_blocklist():
    """Create a temporary blocklist file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Test blocklist\n")
        f.write("example-bad.com\n")
        f.write("test-blocked.org\n")
        f.write("adult-content.net\n")
        blocklist_path = f.name

    yield blocklist_path

    try:
        os.unlink(blocklist_path)
    except Exception:
        pass
