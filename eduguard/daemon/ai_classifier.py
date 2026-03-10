"""
AI classifier module - uses Claude API for content classification
"""
import logging
import os
from typing import Dict, Optional
from datetime import datetime
import anthropic

logger = logging.getLogger(__name__)


class AIClassifier:
    """Uses Claude API to classify website content"""

    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.api_key = os.environ.get('ANTHROPIC_API_KEY', config['ai'].get('api_key', ''))
        self.model = config['ai']['model']
        self.confidence_threshold = config['ai']['confidence_threshold']
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def classify_batch(self, domains: list) -> Dict[str, Dict]:
        """Classify a batch of domains using Claude API"""
        if not self.client:
            logger.warning("Claude API key not configured")
            return {}

        results = {}
        try:
            for domain in domains:
                # Check cache first
                cached = self._get_cached_decision(domain)
                if cached:
                    results[domain] = cached
                    continue

                # Classify using AI
                decision = self._classify_domain(domain)
                if decision:
                    results[domain] = decision
                    self._cache_decision(domain, decision)

            logger.info(f"Classified {len(results)} domains")
        except Exception as e:
            logger.error(f"Error in batch classification: {e}", exc_info=True)

        return results

    def _classify_domain(self, domain: str) -> Optional[Dict]:
        """Classify a single domain"""
        try:
            prompt = f"""You are a parental control content classifier. Analyze this domain and determine if it's appropriate for a 10-year-old child.

Domain: {domain}

Respond with a JSON object containing:
- "decision": "allow" or "block"
- "reason": Brief explanation (1-2 sentences)
- "confidence": Float between 0 and 1

Consider:
- Educational content: ALLOW
- Age-appropriate entertainment: ALLOW
- Social media (unrestricted): BLOCK
- Adult content, violence, gambling: BLOCK
- Unknown/suspicious domains: BLOCK (better safe than sorry)"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = message.content[0].text
            # Simple parsing (in production, use proper JSON parsing)
            decision = 'block'
            reason = 'AI classification'
            confidence = 0.8

            if 'allow' in response_text.lower():
                decision = 'allow'
            if 'reason' in response_text.lower():
                lines = response_text.split('\n')
                for line in lines:
                    if 'reason' in line.lower():
                        reason = line.split(':', 1)[1].strip().strip('"\'')
                        break

            return {
                'decision': decision,
                'reason': reason,
                'confidence': confidence
            }

        except Exception as e:
            logger.error(f"Error classifying domain {domain}: {e}")
            return None

    def _get_cached_decision(self, domain: str) -> Optional[Dict]:
        """Get cached AI decision for domain"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT decision, reason, confidence
                    FROM ai_decisions
                    WHERE domain = ?
                """, (domain,))
                result = cursor.fetchone()
                if result:
                    return {
                        'decision': result['decision'],
                        'reason': result['reason'],
                        'confidence': result['confidence']
                    }
        except Exception as e:
            logger.error(f"Error getting cached decision: {e}")
        return None

    def _cache_decision(self, domain: str, decision: Dict):
        """Cache AI decision for domain"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_decisions (domain, decision, reason, confidence, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (domain, decision['decision'], decision['reason'], decision['confidence']))
        except Exception as e:
            logger.error(f"Error caching decision: {e}")

    def generate_daily_insights(self):
        """Generate AI-powered daily activity summary"""
        if not self.client:
            logger.warning("Claude API key not configured")
            return

        try:
            # Get today's activity data
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Get screen time
                cursor.execute("""
                    SELECT SUM(duration_seconds) as total_time
                    FROM usage_sessions
                    WHERE DATE(start_time) = DATE('now')
                """)
                screen_time = cursor.fetchone()['total_time'] or 0

                # Get top visited sites
                cursor.execute("""
                    SELECT url, COUNT(*) as visits
                    FROM browser_visits
                    WHERE DATE(visit_time) = DATE('now')
                    GROUP BY url
                    ORDER BY visits DESC
                    LIMIT 10
                """)
                top_sites = cursor.fetchall()

                # Get blocked attempts
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM blocked_attempts
                    WHERE DATE(timestamp) = DATE('now')
                """)
                blocked_count = cursor.fetchone()['count']

            # Generate insight using Claude
            activity_summary = f"""Screen time: {screen_time // 60} minutes
Top visited sites: {', '.join([row['url'] for row in top_sites[:5]])}
Blocked attempts: {blocked_count}"""

            prompt = f"""Generate a brief, natural-language summary of this child's daily internet activity for their parent. Focus on patterns, concerns, and positive behaviors.

{activity_summary}

Keep it concise (2-3 sentences) and constructive."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )

            insight = message.content[0].text

            # Save insight
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_insights (insight_type, content, summary)
                    VALUES (?, ?, ?)
                """, ('daily_summary', activity_summary, insight))

            logger.info("Generated daily AI insight")

        except Exception as e:
            logger.error(f"Error generating insights: {e}", exc_info=True)
