"""
EduGuard daemon - main service process
"""
import os
import sys
import signal
import logging
import yaml
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from eduguard.daemon.database import Database
from eduguard.daemon.time_tracker import TimeTracker
from eduguard.daemon.enforcer import Enforcer
from eduguard.daemon.browser_monitor import BrowserMonitor
from eduguard.daemon.dns_proxy import DNSProxy
from eduguard.daemon.ai_classifier import AIClassifier

logger = logging.getLogger(__name__)


class EduGuardDaemon:
    """Main daemon process for EduGuard"""

    def __init__(self, config_path: str = '/etc/eduguard/eduguard.yaml'):
        self.config_path = config_path
        self.config = None
        self.db = None
        self.scheduler = None
        self.time_tracker = None
        self.enforcer = None
        self.browser_monitor = None
        self.dns_proxy = None
        self.ai_classifier = None

        self._load_config()
        self._setup_logging()
        self._init_components()
        self._setup_scheduler()
        self._setup_signal_handlers()

    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            # Try multiple config locations
            config_paths = [
                self.config_path,
                '/etc/eduguard/eduguard.yaml',
                Path(__file__).parent.parent / 'config' / 'eduguard.yaml'
            ]

            for path in config_paths:
                if Path(path).exists():
                    with open(path, 'r') as f:
                        self.config = yaml.safe_load(f)
                    logger.info(f"Loaded config from {path}")
                    return

            raise FileNotFoundError("Config file not found in any location")

        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config['logging']['level'], logging.INFO)
        log_file = self.config['logging']['file']

        # Ensure log directory exists
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def _init_components(self):
        """Initialize all daemon components"""
        try:
            # Initialize database
            db_path = self.config['database']['path']
            self.db = Database(db_path)
            logger.info("Database initialized")

            # Initialize components
            self.time_tracker = TimeTracker(self.db, self.config)
            self.enforcer = Enforcer(self.db, self.config)
            self.browser_monitor = BrowserMonitor(self.db, self.config)
            self.dns_proxy = DNSProxy(self.db, self.config)
            self.ai_classifier = AIClassifier(self.db, self.config)

            logger.info("All components initialized")

        except Exception as e:
            logger.error(f"Error initializing components: {e}", exc_info=True)
            sys.exit(1)

    def _setup_scheduler(self):
        """Setup APScheduler with all jobs"""
        jobstores = {'default': MemoryJobStore()}
        executors = {'default': ThreadPoolExecutor(max_workers=1)}
        job_defaults = {'coalesce': True, 'max_instances': 1}

        self.scheduler = BlockingScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )

        # Time tracking job - every 60 seconds
        self.scheduler.add_job(
            self._time_tracking_job,
            'interval',
            seconds=self.config['tracking']['poll_interval'],
            id='time_tracking',
            name='Time Tracking'
        )

        # Enforcer job - every 60 seconds
        self.scheduler.add_job(
            self._enforcer_job,
            'interval',
            seconds=60,
            id='enforcer',
            name='Enforcer'
        )

        # Browser monitor job - every 5 minutes
        self.scheduler.add_job(
            self._browser_monitor_job,
            'interval',
            seconds=self.config['browser']['check_interval'],
            id='browser_monitor',
            name='Browser Monitor'
        )

        # DNS update job - every hour
        self.scheduler.add_job(
            self._dns_update_job,
            'interval',
            seconds=3600,
            id='dns_update',
            name='DNS Update'
        )

        # AI batch classification - daily at 2 AM
        self.scheduler.add_job(
            self._ai_batch_job,
            'cron',
            hour=2,
            minute=0,
            id='ai_batch',
            name='AI Batch Classification'
        )

        # AI insights generation - daily at 8 PM
        self.scheduler.add_job(
            self._ai_insights_job,
            'cron',
            hour=20,
            minute=0,
            id='ai_insights',
            name='AI Insights'
        )

        # Daily reset job - at midnight
        self.scheduler.add_job(
            self._daily_reset_job,
            'cron',
            hour=0,
            minute=0,
            id='daily_reset',
            name='Daily Reset'
        )

        logger.info("Scheduler configured with all jobs")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown and reload"""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGUSR1, self._handle_reload)
        logger.info("Signal handlers configured")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        if self.scheduler:
            self.scheduler.shutdown()
        sys.exit(0)

    def _handle_reload(self, signum, frame):
        """Handle reload signal (SIGUSR1)"""
        logger.info("Received reload signal, reloading configuration...")
        try:
            self._load_config()
            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")

    def _time_tracking_job(self):
        """Time tracking job"""
        try:
            self._log_job_start('time_tracking')
            self.time_tracker.track_usage()
            self._log_job_complete('time_tracking')
        except Exception as e:
            self._log_job_error('time_tracking', str(e))

    def _enforcer_job(self):
        """Enforcer job"""
        try:
            self._log_job_start('enforcer')
            self.enforcer.check_and_enforce(self.time_tracker)
            self._log_job_complete('enforcer')
        except Exception as e:
            self._log_job_error('enforcer', str(e))

    def _browser_monitor_job(self):
        """Browser monitor job"""
        try:
            self._log_job_start('browser_monitor')
            self.browser_monitor.check_browser_history()
            self._log_job_complete('browser_monitor')
        except Exception as e:
            self._log_job_error('browser_monitor', str(e))

    def _dns_update_job(self):
        """DNS update job"""
        try:
            self._log_job_start('dns_update')
            self.dns_proxy.update_dnsmasq_config()
            self._log_job_complete('dns_update')
        except Exception as e:
            self._log_job_error('dns_update', str(e))

    def _ai_batch_job(self):
        """AI batch classification job"""
        try:
            self._log_job_start('ai_batch')
            # Get unclassified domains from browser visits
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT
                        SUBSTR(url, INSTR(url, '://') + 3) as domain
                    FROM browser_visits
                    WHERE SUBSTR(url, INSTR(url, '://') + 3) NOT IN (
                        SELECT domain FROM ai_decisions
                    )
                    LIMIT 100
                """)
                domains = [row['domain'].split('/')[0] for row in cursor.fetchall()]

            if domains:
                self.ai_classifier.classify_batch(domains)

            self._log_job_complete('ai_batch')
        except Exception as e:
            self._log_job_error('ai_batch', str(e))

    def _ai_insights_job(self):
        """AI insights generation job"""
        try:
            self._log_job_start('ai_insights')
            self.ai_classifier.generate_daily_insights()
            self._log_job_complete('ai_insights')
        except Exception as e:
            self._log_job_error('ai_insights', str(e))

    def _daily_reset_job(self):
        """Daily reset job"""
        try:
            self._log_job_start('daily_reset')
            self.enforcer.reset_daily_locks()
            self._log_job_complete('daily_reset')
        except Exception as e:
            self._log_job_error('daily_reset', str(e))

    def _log_job_start(self, job_name: str):
        """Log job start"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO job_runs (job_name, status)
                    VALUES (?, 'started')
                """, (job_name,))
        except Exception as e:
            logger.error(f"Error logging job start: {e}")

    def _log_job_complete(self, job_name: str):
        """Log job completion"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE job_runs
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE job_name = ? AND status = 'started'
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (job_name,))
        except Exception as e:
            logger.error(f"Error logging job completion: {e}")

    def _log_job_error(self, job_name: str, error: str):
        """Log job error"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE job_runs
                    SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE job_name = ? AND status = 'started'
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (error, job_name))
        except Exception as e:
            logger.error(f"Error logging job error: {e}")

    def run(self):
        """Start the daemon"""
        logger.info("Starting EduGuard daemon...")
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Database: {self.config['database']['path']}")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Daemon stopped")


def main():
    """Main entry point"""
    daemon = EduGuardDaemon()
    daemon.run()


if __name__ == '__main__':
    main()
