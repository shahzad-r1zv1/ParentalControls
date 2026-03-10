# EduGuard Architecture Documentation

Technical documentation for developers and system administrators working with EduGuard.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Database Schema](#database-schema)
6. [Job Scheduling](#job-scheduling)
7. [AI Integration](#ai-integration)
8. [Security Model](#security-model)
9. [Development Guide](#development-guide)

---

## System Overview

EduGuard is a Linux-based parental control system designed for Edubuntu that combines:
- Real-time screen time tracking
- DNS-based content filtering
- Browser history monitoring
- Local AI-powered content classification
- Web-based parental dashboard

**Technology Stack:**
- **Backend**: Python 3.8+
- **Web Framework**: Flask 3.0
- **Database**: SQLite with WAL mode
- **Scheduler**: APScheduler 3.10
- **AI**: Ollama (local LLM)
- **DNS**: dnsmasq
- **System Integration**: systemd, loginctl, psutil

**Deployment Model:**
- Single-machine installation
- Root daemon process (systemd managed)
- Local-only web dashboard (127.0.0.1)
- No external dependencies or cloud services

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Child's User Session                    │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Firefox    │────────▶│  DNS Query   │                      │
│  │   Browser    │         │   (dnsmasq)  │                      │
│  └──────────────┘         └──────┬───────┘                      │
│                                   │                               │
└───────────────────────────────────┼───────────────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   DNS Resolution  │
                          │   Port 53         │
                          └─────────┬─────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
        ┌─────▼─────┐      ┌────────▼────────┐    ┌─────▼──────┐
        │  Static   │      │  AI Classifier  │    │  Upstream  │
        │ Blocklist │      │     Cache       │    │    DNS     │
        │ (txt file)│      │  (SQLite DB)    │    │  (8.8.8.8) │
        └───────────┘      └─────────────────┘    └────────────┘
                                    │
                                    │
┌───────────────────────────────────▼───────────────────────────────┐
│                       EduGuard Daemon (Root)                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              APScheduler (Job Coordinator)                 │ │
│  │                  max_instances=1 per job                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ TimeTracker  │  │   Enforcer   │  │BrowserMonitor│          │
│  │  (60 sec)    │  │  (60 sec)    │  │  (5 min)     │          │
│  │              │  │              │  │              │          │
│  │ Polls psutil │  │ Checks limits│  │ Reads Firefox│          │
│  │ for active   │  │ Locks session│  │ places.sqlite│          │
│  │ users        │  │ via loginctl │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────▼─────────────────▼─────────────────▼───────┐          │
│  │            SQLite Database (WAL mode)             │          │
│  │  - usage_sessions    - blocked_attempts           │          │
│  │  - browser_visits    - ai_decisions               │          │
│  │  - ai_insights       - job_runs                   │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  DNSProxy    │  │AIClassifier  │  │  AI Insights │          │
│  │  (hourly)    │  │  (2 AM)      │  │  (8 PM)      │          │
│  │              │  │              │  │              │          │
│  │ Updates      │  │ Batch process│  │ Generates    │          │
│  │ dnsmasq conf │  │ unclassified │  │ daily reports│          │
│  │ Reloads      │  │ domains      │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                 │                                      │
│         │                 └──────────────┐                       │
│         │                                │                       │
│  ┌──────▼────────────────────────────────▼───────────┐          │
│  │          Ollama Client (HTTP)                     │          │
│  │          http://localhost:11434                   │          │
│  └───────────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Local HTTP
                                    │
┌───────────────────────────────────▼───────────────────────────────┐
│                       Ollama Server                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           Local LLM (e.g., Llama 3.2 3B)                    │ │
│  │           Loaded in memory: ~2-4GB RAM                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   Flask Dashboard (Parent Access)                 │
│                   http://127.0.0.1:5000                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Dashboard   │  │   History    │  │   Blocked    │           │
│  │  (Overview)  │  │ (Browsing)   │  │  (Attempts)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Insights   │  │   Reports    │  │   Settings   │           │
│  │  (AI Summary)│  │  (Trends)    │  │  (Config)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                   │
│  ├─ Flask-WTF (CSRF Protection)                                  │
│  ├─ Werkzeug (Password hashing)                                  │
│  └─ SQLite Queries (Read-only)                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. TimeTracker

**Purpose:** Monitor active user sessions and track screen time.

**Implementation:** `eduguard/daemon/time_tracker.py`

**How It Works:**
```python
class TimeTracker:
    def __init__(self, db: Database, config: dict):
        self.db = db
        self.current_session = None

    def track_usage(self):
        """Called every 60 seconds by APScheduler"""
        active_users = self._get_active_users()  # Uses psutil

        if active_users and not self.current_session:
            self._start_session(active_users[0])
        elif not active_users and self.current_session:
            self._end_session()
        elif self.current_session:
            self._update_session()
```

**Key Functions:**
- `_get_active_users()` - Uses `psutil.users()` to detect logged-in users on display `:0`
- `_start_session()` - Creates new record in `usage_sessions` table
- `_update_session()` - Updates duration in real-time
- `_end_session()` - Finalizes session record
- `get_today_usage()` - Calculates total minutes used today

**Database Interactions:**
```sql
-- Insert new session
INSERT INTO usage_sessions (username, start_time, display)
VALUES (?, datetime('now'), ?);

-- Update duration
UPDATE usage_sessions
SET duration_seconds = (CAST((julianday('now') - julianday(start_time)) * 86400 AS INTEGER))
WHERE session_id = ?;

-- Calculate today's total
SELECT COALESCE(SUM(duration_seconds), 0)
FROM usage_sessions
WHERE username = ? AND DATE(start_time) = DATE('now');
```

**Edge Cases Handled:**
- Multiple displays (filters to `:0` only)
- Session crashes (orphaned records cleaned up)
- Rapid login/logout cycles (minimum session duration: 1 second)
- Clock changes (uses monotonic time for duration)

---

### 2. Enforcer

**Purpose:** Lock user sessions when screen time limits are exceeded.

**Implementation:** `eduguard/daemon/enforcer.py`

**How It Works:**
```python
class Enforcer:
    def check_and_enforce(self):
        """Called every 60 seconds by APScheduler"""
        usage = self.time_tracker.get_today_usage()
        limit = self.config['limits']['daily_screen_time'] * 60

        if usage['duration_seconds'] >= limit:
            if not self._is_session_locked(usage['username']):
                self._lock_session(usage['username'])
                self._log_enforcement(usage['username'])
```

**Lock Mechanism:**
```bash
# Find active session
loginctl list-sessions | grep username

# Lock the session
loginctl lock-session <session-id>
```

**Database Interactions:**
```sql
-- Check if already locked today
SELECT locked_at FROM enforcement_locks
WHERE username = ? AND DATE(locked_at) = DATE('now');

-- Log enforcement action
INSERT INTO enforcement_locks (username, reason, locked_at)
VALUES (?, 'Daily limit exceeded', datetime('now'));
```

**Unlock Handling:**
- Automatic unlock at midnight (daily reset job)
- Manual unlock via parent dashboard
- Session remains locked even if user logs out and back in

**Security:**
- Requires root privileges (systemd service runs as root)
- Uses system `loginctl` command (not bypassable by child user)
- Logs all enforcement actions for audit

---

### 3. BrowserMonitor

**Purpose:** Track Firefox browsing history for parental review.

**Implementation:** `eduguard/daemon/browser_monitor.py`

**How It Works:**
```python
class BrowserMonitor:
    def check_history(self):
        """Called every 5 minutes by APScheduler"""
        profile_path = self._find_firefox_profile()

        # Copy places.sqlite to avoid locks
        temp_path = self._copy_database(profile_path)

        # Read visits since last cursor
        visits = self._read_visits(temp_path, self.last_cursor)

        # Save to EduGuard database
        self._save_visits(visits)

        # Update cursor
        self._update_cursor(max(v['visit_date'] for v in visits))
```

**Firefox Database Schema:**
```sql
-- Firefox's places.sqlite structure (simplified)
moz_places:
  - url TEXT
  - title TEXT
  - visit_count INTEGER

moz_historyvisits:
  - place_id INTEGER (FK to moz_places)
  - visit_date INTEGER (microseconds since epoch)
```

**Query Used:**
```sql
SELECT
  p.url,
  p.title,
  h.visit_date,
  p.visit_count
FROM moz_historyvisits h
JOIN moz_places p ON h.place_id = p.id
WHERE h.visit_date > ?
ORDER BY h.visit_date ASC
LIMIT 1000;
```

**Cursor Management:**
- Stores last processed `visit_date` in `browser_history_cursor` table
- Prevents duplicate processing of history
- Handles Firefox database growth efficiently

**Error Handling:**
- Profile detection fails → Logs warning, skips iteration
- Database locked → Copies to temp file first
- Invalid URLs → Sanitizes before storing
- Firefox not installed → Disables monitoring gracefully

---

### 4. DNSProxy

**Purpose:** Block inappropriate domains via dnsmasq DNS server.

**Implementation:** `eduguard/daemon/dns_proxy.py`

**How It Works:**
```python
class DNSProxy:
    def check_domain(self, domain: str) -> bool:
        """Returns True if domain should be blocked"""

        # 1. Check static blocklist
        if domain in self.blocklist:
            self._log_blocked(domain, "Static blocklist")
            return True

        # 2. Check AI decision cache
        decision = self._get_cached_decision(domain)
        if decision and decision['decision'] == 'block':
            self._log_blocked(domain, f"AI: {decision['reason']}")
            return True

        # 3. Queue for AI classification if unknown
        if not decision:
            self._queue_for_classification(domain)

        return False  # Allow by default until classified
```

**dnsmasq Configuration:**
```bash
# Generated in /etc/dnsmasq.d/eduguard.conf
address=/blocked-domain.com/0.0.0.0
address=/another-blocked.com/0.0.0.0
```

**Update Process:**
```python
def update_dnsmasq_config(self):
    """Called hourly by APScheduler"""

    # Get all blocked domains
    blocked = set(self.blocklist)
    blocked.update(self._get_ai_blocked_domains())

    # Generate dnsmasq config
    config_lines = [f"address=/{domain}/0.0.0.0" for domain in blocked]

    # Write to file
    with open(self.config['dns']['dnsmasq_config'], 'w') as f:
        f.write('\n'.join(config_lines))

    # Reload dnsmasq
    subprocess.run(['systemctl', 'reload', 'dnsmasq'])
```

**Logging:**
```sql
INSERT INTO blocked_attempts (domain, blocked_at, reason, source)
VALUES (?, datetime('now'), ?, ?);
```

---

### 5. AIClassifier

**Purpose:** Intelligently classify unknown domains using local LLM.

**Implementation:** `eduguard/daemon/ai_classifier.py`

**Architecture:**
```python
class AIClassifier:
    def __init__(self, config: dict, db: Database):
        self.client = ollama.Client(host=config['ai']['ollama_host'])
        self.model = config['ai']['model']  # e.g., 'llama3.2:3b'
        self.db = db

    def batch_classify(self):
        """Called nightly at 2 AM by APScheduler"""

        # Get unclassified domains from browser_visits
        domains = self._get_unclassified_domains()

        for domain in domains:
            decision = self._classify_domain(domain)
            self._cache_decision(domain, decision)
```

**Classification Prompt:**
```python
prompt = f"""Analyze this domain for child safety: {domain}

Respond with JSON only:
{{
  "decision": "allow" or "block",
  "reason": "brief explanation",
  "confidence": 0.0-1.0,
  "category": "educational|entertainment|social_media|adult|gaming|news|shopping|other"
}}

Consider:
- Educational value for children
- Age-appropriate content
- Potential distractions
- Safety concerns

Domain: {domain}"""
```

**Ollama API Call:**
```python
response = self.client.chat(
    model=self.model,
    messages=[{'role': 'user', 'content': prompt}],
    options={
        'temperature': 0.3,  # Low for consistent decisions
        'num_predict': 256,   # Max tokens
    }
)

response_text = response['message']['content']
```

**Response Parsing:**
```python
def _parse_response(self, text: str) -> dict:
    # Try JSON parsing first
    try:
        # Remove markdown code blocks if present
        text = re.sub(r'```json\s*|\s*```', '', text)
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: Extract decision from text
        if 'block' in text.lower():
            return {
                'decision': 'block',
                'reason': 'Content may not be appropriate',
                'confidence': 0.6,
                'category': 'other'
            }
        else:
            return {
                'decision': 'allow',
                'reason': 'No obvious concerns detected',
                'confidence': 0.6,
                'category': 'other'
            }
```

**Caching:**
```sql
-- Store decision in database
INSERT INTO ai_decisions (domain, decision, reason, confidence, category, classified_at)
VALUES (?, ?, ?, ?, ?, datetime('now'));

-- Retrieve cached decision
SELECT decision, reason, confidence, category
FROM ai_decisions
WHERE domain = ?;
```

**Performance:**
- Processes 10-50 domains per batch (typical)
- ~1-2 seconds per classification
- Total batch time: 1-5 minutes
- Model stays loaded in memory (faster subsequent calls)

---

### 6. Dashboard

**Purpose:** Web-based interface for parents to monitor and configure.

**Implementation:** `eduguard/dashboard/app.py`

**Flask Application:**
```python
from flask import Flask, render_template, request, session
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
csrf = CSRFProtect(app)

@app.route('/')
@login_required
def dashboard():
    stats = get_daily_stats()
    return render_template('dashboard.html', stats=stats)
```

**Routes:**
- `GET /` - Dashboard overview
- `GET /history` - Browsing history with filters
- `GET /blocked` - Blocked attempts log
- `GET /insights` - AI-generated insights
- `GET /reports` - Weekly/monthly reports
- `GET /settings` - Configuration page
- `POST /settings` - Update configuration
- `POST /login` - Authentication
- `GET /logout` - End session

**Authentication:**
```python
from werkzeug.security import check_password_hash

def login():
    password = request.form['password']
    stored_hash = os.getenv('PARENT_PASSWORD_HASH')

    if check_password_hash(stored_hash, password):
        session['authenticated'] = True
        return redirect('/')
    else:
        flash('Invalid password')
        return redirect('/login')
```

**Database Queries:**
```python
def get_daily_stats():
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
            WHERE DATE(blocked_at) = DATE('now')
        """)
        blocked = cursor.fetchone()['count']

        return {'screen_time': screen_time, 'blocked': blocked}
```

**Security Features:**
- CSRF protection on all POST requests
- Password hashing with scrypt
- Session timeout (1 hour default)
- Localhost-only binding (127.0.0.1)
- No external JavaScript or CDN dependencies

---

## Data Flow

### Scenario 1: Child Visits Website

```
1. Child enters URL in Firefox
   ↓
2. DNS query sent to dnsmasq (127.0.0.1:53)
   ↓
3. DNSProxy checks domain:
   a. Static blocklist → BLOCK if found
   b. AI cache → BLOCK if classified as block
   c. Unknown → Queue for classification, ALLOW for now
   ↓
4. If allowed, resolve to actual IP
   If blocked, resolve to 0.0.0.0 (page won't load)
   ↓
5. BrowserMonitor (next 5-min cycle):
   - Reads Firefox places.sqlite
   - Extracts visit record
   - Stores in browser_visits table
   ↓
6. AI Batch Job (nightly at 2 AM):
   - Finds unclassified domains from browser_visits
   - Sends to Ollama for classification
   - Caches decision in ai_decisions table
   ↓
7. DNSProxy (next hour update):
   - Regenerates dnsmasq config with new blocks
   - Reloads dnsmasq
   - Future visits to newly-blocked domains are stopped
```

### Scenario 2: Screen Time Limit Reached

```
1. Child logs in at 9:00 AM
   ↓
2. TimeTracker (every 60 seconds):
   - Detects active session via psutil
   - Creates usage_sessions record
   - Updates duration continuously
   ↓
3. At 11:00 AM (120 minutes later):
   Enforcer checks:
   - Queries total time today: 120 minutes
   - Compares to limit: 120 minutes
   - Limit reached!
   ↓
4. Enforcer executes:
   - Finds session ID via loginctl
   - Runs: loginctl lock-session <id>
   - Logs enforcement in database
   ↓
5. Child's screen locks immediately
   - Must re-authenticate to unlock
   - But TimeTracker still counts time
   - Enforcer will re-lock if limit still exceeded
   ↓
6. At midnight:
   Daily Reset job:
   - Clears today's enforcement locks
   - Does NOT delete usage_sessions (kept for reports)
   - Child can use computer again tomorrow
```

### Scenario 3: Parent Views Dashboard

```
1. Parent opens browser → http://127.0.0.1:5000
   ↓
2. Flask checks authentication:
   - Not in session → Redirect to /login
   ↓
3. Parent enters password
   ↓
4. Flask verifies:
   - Hashes password with scrypt
   - Compares to PARENT_PASSWORD_HASH env var
   - Match → Set session cookie
   ↓
5. Dashboard queries SQLite:
   - Screen time today (usage_sessions)
   - Blocked attempts (blocked_attempts)
   - Recent visits (browser_visits)
   - Latest insight (ai_insights)
   ↓
6. Flask renders dashboard.html with data
   ↓
7. Parent can navigate:
   - View history (paginated, filterable)
   - Review AI decisions
   - Adjust settings → Updates eduguard.yaml
   - Changes take effect on next job cycle or reload
```

---

## Database Schema

### Complete Schema

```sql
-- Screen time tracking
CREATE TABLE usage_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER DEFAULT 0,
    display TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_usage_username_date ON usage_sessions(username, start_time);

-- Browser history
CREATE TABLE browser_visits (
    visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    visited_at TIMESTAMP NOT NULL,
    visit_count INTEGER DEFAULT 1,
    domain TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_visits_domain ON browser_visits(domain);
CREATE INDEX idx_visits_date ON browser_visits(visited_at);

-- DNS blocking logs
CREATE TABLE blocked_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    blocked_at TIMESTAMP NOT NULL,
    reason TEXT,
    source TEXT CHECK(source IN ('static', 'ai', 'manual')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_blocked_domain ON blocked_attempts(domain);
CREATE INDEX idx_blocked_date ON blocked_attempts(blocked_at);

-- AI classification cache
CREATE TABLE ai_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    decision TEXT CHECK(decision IN ('allow', 'block')) NOT NULL,
    reason TEXT,
    confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
    category TEXT,
    classified_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_domain ON ai_decisions(domain);
CREATE INDEX idx_ai_decision ON ai_decisions(decision);

-- Application usage (future feature)
CREATE TABLE app_usage (
    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    app_name TEXT NOT NULL,
    window_title TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI-generated insights
CREATE TABLE ai_insights (
    insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    summary TEXT NOT NULL,
    concerns TEXT,
    recommendations TEXT,
    generated_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_insights_date ON ai_insights(date);

-- Configuration audit log
CREATE TABLE config_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at TIMESTAMP NOT NULL,
    changed_by TEXT,
    setting_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job execution tracking
CREATE TABLE job_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT CHECK(status IN ('running', 'success', 'error')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_job_name ON job_runs(job_name);
CREATE INDEX idx_job_started ON job_runs(started_at);

-- Browser sync cursor
CREATE TABLE browser_history_cursor (
    cursor_id INTEGER PRIMARY KEY CHECK(cursor_id = 1),
    last_visit_date INTEGER NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Database Configuration

```python
# SQLite settings for concurrency
conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
```

**Why WAL Mode?**
- Allows concurrent readers and writers
- Dashboard can query while daemon writes
- Better performance for write-heavy workloads
- Automatic checkpointing

---

## Job Scheduling

### APScheduler Configuration

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

scheduler = BackgroundScheduler(
    executors={
        'default': ThreadPoolExecutor(max_workers=5)
    },
    job_defaults={
        'coalesce': True,
        'max_instances': 1,  # Prevent job overlap
        'misfire_grace_time': 300  # 5 minutes
    }
)
```

### Scheduled Jobs

| Job Name | Function | Interval | Purpose |
|----------|----------|----------|---------|
| `time_tracker` | `time_tracker.track_usage()` | Every 60 sec | Poll for active users |
| `enforcer` | `enforcer.check_and_enforce()` | Every 60 sec | Check and enforce limits |
| `browser_monitor` | `browser_monitor.check_history()` | Every 5 min | Read Firefox history |
| `dns_update` | `dns_proxy.update_dnsmasq_config()` | Every 1 hour | Update DNS blocks |
| `ai_batch` | `ai_classifier.batch_classify()` | Daily at 2 AM | Classify domains |
| `ai_insights` | `ai_classifier.generate_insights()` | Daily at 8 PM | Generate summaries |
| `daily_reset` | `reset_daily_counters()` | Daily at midnight | Reset limits |

### Job Monitoring

```python
def log_job_execution(job_name: str, status: str, error: str = None):
    """Track all job runs in database"""
    with db.get_connection() as conn:
        if status == 'started':
            conn.execute("""
                INSERT INTO job_runs (job_name, started_at, status)
                VALUES (?, datetime('now'), 'running')
            """, (job_name,))
        elif status == 'success':
            conn.execute("""
                UPDATE job_runs SET
                    completed_at = datetime('now'),
                    status = 'success'
                WHERE job_name = ? AND status = 'running'
            """, (job_name,))
        elif status == 'error':
            conn.execute("""
                UPDATE job_runs SET
                    completed_at = datetime('now'),
                    status = 'error',
                    error_message = ?
                WHERE job_name = ? AND status = 'running'
            """, (error, job_name))
```

---

## AI Integration

### Ollama Architecture

```
EduGuard AIClassifier
        ↓ HTTP POST
Ollama Server (localhost:11434)
        ↓
Model Loaded in RAM (~2-4GB)
        ↓ Inference
Generated Response
        ↓ HTTP Response
EduGuard AIClassifier
```

### Model Selection Criteria

| Factor | Llama 3.2 3B | Mistral 7B | TinyLlama 1.1B |
|--------|--------------|------------|----------------|
| **RAM** | 4GB | 8GB | 2GB |
| **Speed** | 1-2s | 3-5s | 0.5-1s |
| **Accuracy** | 85-90% | 90-95% | 70-80% |
| **Best For** | Standard use | High accuracy | Low-end hardware |

### Prompt Engineering

**Key Principles:**
1. **Structured Output**: Request JSON for easy parsing
2. **Clear Criteria**: List specific safety factors to consider
3. **Low Temperature**: 0.3 for consistent decisions
4. **Token Limit**: 256 tokens sufficient for classification
5. **Fallback Parsing**: Handle non-JSON responses gracefully

**Example Effective Prompt:**
```
You are a content safety classifier for children ages 8-14.

Analyze: example.com

Output valid JSON:
{
  "decision": "allow|block",
  "reason": "one sentence",
  "confidence": 0.0-1.0,
  "category": "educational|entertainment|social_media|adult|gaming|news|shopping|other"
}

Block if:
- Adult/mature content
- Violence, weapons, drugs
- Social media (time-wasting)
- Gambling, betting
- User-generated content without moderation

Allow if:
- Educational resources
- Age-appropriate games
- Informational content
- Supervised platforms
```

### Caching Strategy

**Why Cache?**
- Avoid re-classifying same domains
- Instant blocking decisions
- Reduced Ollama load
- Consistent decisions over time

**Cache Invalidation:**
- Manual override by parent
- Never auto-expires (manual clear only)
- Can be exported/imported for sharing

**Cache Hit Rate:**
- Typical: 80-90% (most visits are to known sites)
- First week: 40-60% (building cache)
- After month: 95%+ (stable cache)

---

## Security Model

### Threat Model

**Assets to Protect:**
1. Child's screen time limits
2. Content filtering rules
3. Browsing history data
4. Parent dashboard access

**Threats Considered:**
- Child attempting to bypass limits
- Unauthorized access to parent dashboard
- Tampering with database or configs
- Network-level bypass (VPN, alternative DNS)

**Not Protected Against:**
- Physical access to BIOS (boot from USB)
- Root/sudo access
- Hardware modifications
- VPN usage (network-level bypass)

### Security Controls

**Privilege Separation:**
```
Root (daemon):
  - Read/write /var/lib/eduguard/
  - Modify dnsmasq config
  - Execute loginctl commands
  - System service management

Parent (dashboard user):
  - Read-only database access
  - Write config via authenticated web UI
  - No direct system access

Child (restricted user):
  - No access to /var/lib/eduguard/
  - No sudo privileges
  - No access to systemd services
  - Cannot modify dnsmasq or DNS settings
```

**File Permissions:**
```bash
/var/lib/eduguard/eduguard.db        # 600 root:root
/etc/eduguard/eduguard.yaml          # 600 root:root
/etc/eduguard/env/eduguard.env       # 600 root:root
/var/log/eduguard/eduguard.log       # 640 root:root
/etc/dnsmasq.d/eduguard.conf         # 644 root:root
```

**Network Security:**
- Dashboard bound to 127.0.0.1 only (no remote access)
- No external API calls (all processing local)
- DNS queries stay on local machine
- No telemetry or phoning home

**Authentication:**
- Password hashing: scrypt (CPU + memory hard)
- Session cookies: HTTPOnly, Secure flags
- CSRF protection: Flask-WTF tokens on all forms
- Session timeout: 1 hour default

**Audit Logging:**
- All configuration changes logged
- All enforcement actions logged
- Job execution tracked
- Dashboard access logged (via Flask logs)

---

## Development Guide

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/eduguard.git
cd eduguard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .
pip install pytest pytest-cov pytest-mock

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:3b

# Create test config
mkdir -p /tmp/eduguard
cp eduguard/config/eduguard.yaml /tmp/eduguard/
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_database.py

# Run with coverage
pytest --cov=eduguard --cov-report=html tests/

# Run only unit tests
pytest -m unit tests/

# Run only integration tests
pytest -m integration tests/
```

### Running Components Manually

```bash
# Run daemon in foreground (debug mode)
sudo python3 -m eduguard.daemon.daemon

# Run dashboard with debug
FLASK_DEBUG=1 python3 -m eduguard.dashboard.app

# Test individual components
python3 -c "
from eduguard.daemon.database import Database
db = Database('/tmp/test.db')
print('Tables:', db.get_tables())
"
```

### Code Structure Best Practices

**Module Organization:**
```
eduguard/
├── __init__.py            # Package metadata
├── config/
│   └── eduguard.yaml      # Default configuration
├── daemon/
│   ├── __init__.py
│   ├── daemon.py          # Main orchestrator
│   ├── database.py        # Schema + connection management
│   ├── time_tracker.py    # Feature module
│   ├── enforcer.py        # Feature module
│   ├── browser_monitor.py # Feature module
│   ├── dns_proxy.py       # Feature module
│   └── ai_classifier.py   # Feature module
└── dashboard/
    ├── __init__.py
    ├── app.py             # Flask application
    ├── templates/         # HTML templates
    └── static/            # CSS, JS, images
```

**Coding Standards:**
- Python 3.8+ features
- Type hints encouraged
- Docstrings for public functions
- Unit tests for all business logic
- Integration tests for database queries
- Error handling with logging
- No global state (except scheduler)

### Adding New Features

**Example: Add YouTube Time Limits**

1. **Update Schema:**
   ```sql
   ALTER TABLE usage_sessions ADD COLUMN youtube_seconds INTEGER DEFAULT 0;
   ```

2. **Add Configuration:**
   ```yaml
   limits:
     daily_screen_time: 120
     youtube_time: 30  # NEW
   ```

3. **Create Feature Module:**
   ```python
   # eduguard/daemon/youtube_tracker.py
   class YouTubeTracker:
       def track_youtube_usage(self):
           # Implementation
   ```

4. **Integrate in Daemon:**
   ```python
   # eduguard/daemon/daemon.py
   youtube_tracker = YouTubeTracker(db, config)
   scheduler.add_job(youtube_tracker.track_youtube_usage, 'interval', minutes=1)
   ```

5. **Update Dashboard:**
   ```html
   <!-- Show YouTube usage in dashboard -->
   <div class="youtube-usage">{{ youtube_minutes }} / {{ youtube_limit }} min</div>
   ```

6. **Write Tests:**
   ```python
   # tests/unit/test_youtube_tracker.py
   def test_youtube_tracking():
       # Test implementation
   ```

---

## Performance Considerations

### Resource Usage

**Typical Runtime:**
- **CPU**: 1-5% (idle), 10-20% (during AI batch)
- **RAM**: 100MB (daemon) + 2-4GB (Ollama model)
- **Disk**: 10MB/day (database growth)
- **Network**: 0 (all local)

**Scalability:**
- Designed for single-user/family use
- Database handles 10+ years of data (with cleanup)
- AI batch processes 100s of domains efficiently
- Dashboard supports multiple concurrent parent logins

### Optimization Tips

**Database:**
```sql
-- Regular maintenance
VACUUM;
ANALYZE;
PRAGMA optimize;

-- Archive old data
DELETE FROM usage_sessions WHERE start_time < date('now', '-1 year');
DELETE FROM browser_visits WHERE visited_at < date('now', '-6 months');
```

**AI Performance:**
```yaml
# Use smaller model for faster classification
ai:
  model: tinyllama:1.1b  # 3x faster than llama3.2:3b

# Reduce batch frequency if not needed daily
ai:
  batch_interval: 172800  # Every 2 days
```

**Monitoring:**
```bash
# Check database size
du -sh /var/lib/eduguard/eduguard.db

# Check job execution times
sqlite3 /var/lib/eduguard/eduguard.db "
SELECT job_name,
       AVG((julianday(completed_at) - julianday(started_at)) * 86400) as avg_duration_sec
FROM job_runs
WHERE status='success'
GROUP BY job_name;
"
```

---

**Last Updated:** March 2026
**Version:** 1.0.0
**For:** EduGuard Parental Control System
**Maintainer:** EduGuard Development Team
