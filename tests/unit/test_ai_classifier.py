"""
Unit tests for AIClassifier module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from eduguard.daemon.ai_classifier import AIClassifier


@pytest.mark.unit
class TestAIClassifier:
    """Test AIClassifier class functionality"""

    @pytest.fixture
    def ai_classifier(self, temp_db, test_config):
        """Create an AIClassifier instance for testing"""
        with patch('eduguard.daemon.ai_classifier.ollama.Client'):
            classifier = AIClassifier(temp_db, test_config)
            # Mock the client
            classifier.client = Mock()
            return classifier

    def test_initialization(self, ai_classifier):
        """Test AIClassifier initialization"""
        assert ai_classifier.db is not None
        assert ai_classifier.config is not None
        assert ai_classifier.model == 'llama3.2:3b'
        assert ai_classifier.ollama_host == 'http://localhost:11434'

    def test_initialization_no_ollama(self, temp_db, test_config):
        """Test initialization when Ollama not available"""
        with patch('eduguard.daemon.ai_classifier.ollama.Client', side_effect=Exception("Connection failed")):
            classifier = AIClassifier(temp_db, test_config)
            assert classifier.client is None

    def test_classify_domain_success(self, ai_classifier):
        """Test successful domain classification"""
        # Mock Ollama response with JSON
        mock_response = {
            'message': {
                'content': json.dumps({
                    'decision': 'block',
                    'reason': 'Adult content detected',
                    'confidence': 0.95
                })
            }
        }
        ai_classifier.client.chat.return_value = mock_response

        result = ai_classifier._classify_domain('bad-site.com')

        assert result is not None
        assert result['decision'] == 'block'
        assert result['reason'] == 'Adult content detected'
        assert result['confidence'] == 0.95

    def test_classify_domain_with_markdown(self, ai_classifier):
        """Test classification with markdown code blocks"""
        # Mock response with markdown formatting
        mock_response = {
            'message': {
                'content': '```json\n{"decision": "allow", "reason": "Educational content", "confidence": 0.88}\n```'
            }
        }
        ai_classifier.client.chat.return_value = mock_response

        result = ai_classifier._classify_domain('edu-site.org')

        assert result is not None
        assert result['decision'] == 'allow'
        assert result['reason'] == 'Educational content'

    def test_classify_domain_fallback_parsing(self, ai_classifier):
        """Test fallback parsing when JSON fails"""
        # Mock non-JSON response
        mock_response = {
            'message': {
                'content': 'Decision: allow\nReason: This is a safe educational website for children.\nConfidence: 0.9'
            }
        }
        ai_classifier.client.chat.return_value = mock_response

        result = ai_classifier._classify_domain('safe-site.com')

        assert result is not None
        assert result['decision'] == 'allow'
        # Should have parsed the reason
        assert 'safe educational website' in result['reason'].lower()

    def test_classify_domain_error(self, ai_classifier):
        """Test error handling in domain classification"""
        ai_classifier.client.chat.side_effect = Exception("API error")

        result = ai_classifier._classify_domain('test.com')

        assert result is None

    def test_get_cached_decision(self, ai_classifier):
        """Test retrieving cached decision"""
        # Insert cached decision
        with ai_classifier.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions (domain, decision, reason, confidence)
                VALUES (?, ?, ?, ?)
            """, ('cached.com', 'allow', 'Previously classified', 0.9))

        cached = ai_classifier._get_cached_decision('cached.com')

        assert cached is not None
        assert cached['decision'] == 'allow'
        assert cached['reason'] == 'Previously classified'
        assert cached['confidence'] == 0.9

    def test_get_cached_decision_not_found(self, ai_classifier):
        """Test cached decision not found"""
        cached = ai_classifier._get_cached_decision('unknown.com')
        assert cached is None

    def test_cache_decision(self, ai_classifier):
        """Test caching a decision"""
        decision = {
            'decision': 'block',
            'reason': 'Test reason',
            'confidence': 0.85
        }

        ai_classifier._cache_decision('new-domain.com', decision)

        # Verify cached
        with ai_classifier.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ai_decisions WHERE domain = ?
            """, ('new-domain.com',))
            result = cursor.fetchone()

            assert result is not None
            assert result['decision'] == 'block'
            assert result['confidence'] == 0.85

    def test_classify_batch(self, ai_classifier):
        """Test batch classification"""
        # Mock responses
        def mock_chat(**kwargs):
            content = kwargs['messages'][0]['content']
            if 'domain1.com' in content:
                return {'message': {'content': '{"decision": "block", "reason": "Bad", "confidence": 0.9}'}}
            else:
                return {'message': {'content': '{"decision": "allow", "reason": "Good", "confidence": 0.8}'}}

        ai_classifier.client.chat = mock_chat

        domains = ['domain1.com', 'domain2.org']
        results = ai_classifier.classify_batch(domains)

        assert len(results) == 2
        assert results['domain1.com']['decision'] == 'block'
        assert results['domain2.org']['decision'] == 'allow'

    def test_classify_batch_with_cache(self, ai_classifier):
        """Test batch classification uses cache"""
        # Cache one domain
        with ai_classifier.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions (domain, decision, reason, confidence)
                VALUES (?, ?, ?, ?)
            """, ('cached.com', 'block', 'Cached decision', 0.95))

        # Mock for non-cached domain
        mock_response = {
            'message': {
                'content': '{"decision": "allow", "reason": "New decision", "confidence": 0.85}'
            }
        }
        ai_classifier.client.chat.return_value = mock_response

        domains = ['cached.com', 'new.com']
        results = ai_classifier.classify_batch(domains)

        assert len(results) == 2
        assert results['cached.com']['reason'] == 'Cached decision'
        assert results['new.com']['reason'] == 'New decision'

    def test_classify_batch_no_client(self, ai_classifier):
        """Test batch classification without client"""
        ai_classifier.client = None

        results = ai_classifier.classify_batch(['test.com'])

        assert len(results) == 0

    def test_generate_daily_insights(self, ai_classifier):
        """Test generating daily insights"""
        # Insert test activity data
        with ai_classifier.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_sessions (start_time, duration_seconds, user_name)
                VALUES (datetime('now'), 3600, 'testuser')
            """)
            cursor.execute("""
                INSERT INTO browser_visits (url, visit_time, user_name)
                VALUES
                ('https://example.com', datetime('now'), 'testuser'),
                ('https://test.org', datetime('now'), 'testuser')
            """)
            cursor.execute("""
                INSERT INTO blocked_attempts (domain, reason, user_name)
                VALUES ('bad.com', 'Test', 'testuser')
            """)

        # Mock Ollama response
        mock_response = {
            'message': {
                'content': 'The child spent 60 minutes online today, mostly on educational sites. One blocking occurred, showing good filtering is working.'
            }
        }
        ai_classifier.client.chat.return_value = mock_response

        ai_classifier.generate_daily_insights()

        # Verify insight saved
        with ai_classifier.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ai_insights WHERE insight_type = 'daily_summary'
                ORDER BY generated_at DESC LIMIT 1
            """)
            insight = cursor.fetchone()

            assert insight is not None
            assert 'educational sites' in insight['summary'].lower()

    def test_generate_daily_insights_no_client(self, ai_classifier):
        """Test insights generation without client"""
        ai_classifier.client = None

        # Should not raise exception
        ai_classifier.generate_daily_insights()
