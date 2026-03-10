"""
Flask dashboard application
"""
import os
import signal
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from eduguard.daemon.database import Database

app = Flask(__name__,
            template_folder='../../templates',
            static_folder='../../static')
csrf = CSRFProtect(app)

# Configuration
CONFIG_PATH = os.environ.get('EDUGUARD_CONFIG', '/etc/eduguard/eduguard.yaml')


def load_config():
    """Load configuration"""
    config_paths = [
        CONFIG_PATH,
        '/etc/eduguard/eduguard.yaml',
        Path(__file__).parent.parent / 'config' / 'eduguard.yaml'
    ]

    for path in config_paths:
        if Path(path).exists():
            with open(path, 'r') as f:
                return yaml.safe_load(f)

    raise FileNotFoundError("Config file not found")


config = load_config()
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', config['dashboard'].get('secret_key', 'dev-secret-key'))

# Initialize database
db = Database(config['database']['path'])


def login_required(f):
    """Decorator to require login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        # Simple password check (in production, use proper authentication)
        # Default password: "parent123"
        stored_hash = os.environ.get('PARENT_PASSWORD_HASH',
                                      generate_password_hash('parent123'))

        if check_password_hash(stored_hash, password):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    """Main dashboard"""
    # Get today's statistics
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Screen time today
        cursor.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0) as total
            FROM usage_sessions
            WHERE DATE(start_time) = DATE('now')
        """)
        screen_time = cursor.fetchone()['total']

        # Blocked attempts today
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM blocked_attempts
            WHERE DATE(timestamp) = DATE('now')
        """)
        blocked_today = cursor.fetchone()['count']

        # Top visited sites today
        cursor.execute("""
            SELECT url, COUNT(*) as visits
            FROM browser_visits
            WHERE DATE(visit_time) = DATE('now')
            GROUP BY url
            ORDER BY visits DESC
            LIMIT 10
        """)
        top_sites = cursor.fetchall()

        # Latest AI insight
        cursor.execute("""
            SELECT summary, generated_at
            FROM ai_insights
            ORDER BY generated_at DESC
            LIMIT 1
        """)
        latest_insight = cursor.fetchone()

    stats = {
        'screen_time_minutes': screen_time // 60,
        'screen_time_limit': config['limits']['daily_screen_time'],
        'blocked_today': blocked_today,
        'top_sites': top_sites,
        'latest_insight': latest_insight
    }

    return render_template('dashboard.html', stats=stats)


@app.route('/history')
@login_required
def history():
    """Browsing history"""
    days = int(request.args.get('days', 7))

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, title, visit_time, visit_count
            FROM browser_visits
            WHERE visit_time >= datetime('now', '-' || ? || ' days')
            ORDER BY visit_time DESC
            LIMIT 100
        """, (days,))
        visits = cursor.fetchall()

    return render_template('history.html', visits=visits, days=days)


@app.route('/blocked')
@login_required
def blocked():
    """Blocked attempts"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT domain, reason, timestamp
            FROM blocked_attempts
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        attempts = cursor.fetchall()

    return render_template('blocked.html', attempts=attempts)


@app.route('/insights')
@login_required
def insights():
    """AI insights"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT insight_type, summary, generated_at
            FROM ai_insights
            ORDER BY generated_at DESC
            LIMIT 30
        """)
        insights = cursor.fetchall()

    return render_template('insights.html', insights=insights)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Settings page"""
    if request.method == 'POST':
        try:
            # Update configuration
            new_limit = int(request.form.get('daily_limit', 120))

            # Load current config
            with open(CONFIG_PATH, 'r') as f:
                config_data = yaml.safe_load(f)

            # Update values
            config_data['limits']['daily_screen_time'] = new_limit

            # Save config
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(config_data, f)

            # Log config change
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO config_audit (changed_by, changes)
                    VALUES (?, ?)
                """, ('parent', f"Updated daily limit to {new_limit} minutes"))

            # Send SIGUSR1 to daemon to reload config
            try:
                # Find daemon PID
                pid_file = Path('/var/run/eduguard.pid')
                if pid_file.exists():
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, signal.SIGUSR1)
                    flash('Settings updated and daemon reloaded', 'success')
                else:
                    flash('Settings saved but daemon not running', 'warning')
            except Exception as e:
                flash(f'Settings saved but failed to reload daemon: {e}', 'warning')

            return redirect(url_for('settings'))

        except Exception as e:
            flash(f'Error saving settings: {e}', 'error')

    return render_template('settings.html', config=config)


@app.route('/reports')
@login_required
def reports():
    """Activity reports"""
    # Get weekly statistics
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Daily screen time for last 7 days
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

        # Most visited sites this week
        cursor.execute("""
            SELECT url, COUNT(*) as visits
            FROM browser_visits
            WHERE visit_time >= datetime('now', '-7 days')
            GROUP BY url
            ORDER BY visits DESC
            LIMIT 20
        """)
        top_sites_week = cursor.fetchall()

    return render_template('reports.html',
                         daily_usage=daily_usage,
                         top_sites_week=top_sites_week)


def run_dashboard():
    """Run the dashboard"""
    host = config['dashboard']['host']
    port = config['dashboard']['port']
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_dashboard()
