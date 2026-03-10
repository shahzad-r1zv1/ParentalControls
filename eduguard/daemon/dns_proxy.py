"""
DNS proxy module - integrates with dnsmasq for content filtering
"""
import logging
import subprocess
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class DNSProxy:
    """Manages DNS-based content filtering via dnsmasq"""

    def __init__(self, database, config):
        self.db = database
        self.config = config
        self.blocklist_path = config['dns']['blocklist_path']
        self.dnsmasq_config_path = config['dns']['dnsmasq_config']
        self.blocked_domains = set()
        self._load_blocklist()

    def _load_blocklist(self):
        """Load static blocklist from file"""
        try:
            blocklist_file = Path(self.blocklist_path)
            if blocklist_file.exists():
                with open(blocklist_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.blocked_domains.add(line)
                logger.info(f"Loaded {len(self.blocked_domains)} domains from blocklist")
            else:
                logger.warning(f"Blocklist file not found: {self.blocklist_path}")
        except Exception as e:
            logger.error(f"Error loading blocklist: {e}")

    def update_dnsmasq_config(self):
        """Update dnsmasq configuration with blocked domains"""
        try:
            # Get AI-blocked domains from database
            ai_blocked = self._get_ai_blocked_domains()
            all_blocked = self.blocked_domains.union(ai_blocked)

            # Generate dnsmasq config
            config_lines = [
                "# EduGuard DNS Configuration",
                "# Auto-generated - do not edit manually",
                ""
            ]

            for domain in all_blocked:
                # Redirect blocked domains to localhost
                config_lines.append(f"address=/{domain}/127.0.0.1")

            # Write config file
            config_path = Path(self.dnsmasq_config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w') as f:
                f.write('\n'.join(config_lines))

            logger.info(f"Updated dnsmasq config with {len(all_blocked)} blocked domains")

            # Reload dnsmasq
            self._reload_dnsmasq()

        except Exception as e:
            logger.error(f"Error updating dnsmasq config: {e}", exc_info=True)

    def _get_ai_blocked_domains(self) -> Set[str]:
        """Get domains blocked by AI classifier"""
        domains = set()
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT domain FROM ai_decisions
                    WHERE decision = 'block'
                """)
                for row in cursor.fetchall():
                    domains.add(row['domain'])
        except Exception as e:
            logger.error(f"Error getting AI blocked domains: {e}")
        return domains

    def _reload_dnsmasq(self):
        """Reload dnsmasq service"""
        try:
            result = subprocess.run(
                ['systemctl', 'reload', 'dnsmasq'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("dnsmasq reloaded successfully")
            else:
                logger.error(f"Failed to reload dnsmasq: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("Timeout reloading dnsmasq")
        except Exception as e:
            logger.error(f"Error reloading dnsmasq: {e}")

    def check_domain(self, domain: str) -> bool:
        """Check if a domain should be blocked"""
        # Check static blocklist
        if domain in self.blocked_domains:
            self._log_blocked_attempt(domain, "Static blocklist")
            return True

        # Check AI decisions cache
        decision = self._get_cached_decision(domain)
        if decision and decision['decision'] == 'block':
            self._log_blocked_attempt(domain, f"AI: {decision['reason']}")
            return True

        return False

    def _get_cached_decision(self, domain: str):
        """Get cached AI decision"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT decision, reason FROM ai_decisions
                    WHERE domain = ?
                """, (domain,))
                result = cursor.fetchone()
                if result:
                    return {'decision': result['decision'], 'reason': result['reason']}
        except Exception as e:
            logger.error(f"Error checking domain cache: {e}")
        return None

    def _log_blocked_attempt(self, domain: str, reason: str):
        """Log a blocked access attempt"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO blocked_attempts (domain, reason, user_name)
                    VALUES (?, ?, ?)
                """, (domain, reason, 'child'))
        except Exception as e:
            logger.error(f"Error logging blocked attempt: {e}")
