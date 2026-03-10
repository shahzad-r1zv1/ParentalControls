# EduGuard User Guide

Complete guide to using EduGuard's parental control features to keep your children safe online.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Key Features](#key-features)
4. [How-To Guides](#how-to-guides)
5. [Understanding AI Insights](#understanding-ai-insights)
6. [Troubleshooting Common Issues](#troubleshooting-common-issues)
7. [Best Practices](#best-practices)

---

## Getting Started

### First Time Login

1. Open a web browser on your computer (the same computer where EduGuard is installed)
2. Navigate to: `http://127.0.0.1:5000`
3. Enter the parent password (default: `parent123`)
4. **Important**: Change the default password immediately after first login

### Changing Your Password

```bash
# Generate a new password hash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-new-password'))"

# Update the environment file
sudo nano /etc/eduguard/env/eduguard.env
# Replace PARENT_PASSWORD_HASH with the new hash

# Restart the service
sudo systemctl restart eduguard
```

---

## Dashboard Overview

### Main Dashboard Page

The dashboard provides an at-a-glance overview of your child's daily activity:

**Today's Statistics:**
- **Screen Time**: Total time spent on the computer today
- **Daily Limit**: Configured daily screen time limit (default: 2 hours)
- **Blocked Attempts**: Number of websites blocked today
- **Sites Visited**: Total unique websites visited

**Recent Activity Feed:**
- Most recent browsing activity
- Recently blocked websites
- Session start/end times

### Navigation Menu

- **Dashboard** 🏠 - Overview and daily statistics
- **History** 📜 - Complete browsing history
- **Blocked** 🚫 - Sites that were blocked and why
- **Insights** 💡 - AI-generated activity summaries
- **Reports** 📊 - Weekly and monthly trends
- **Settings** ⚙️ - Configure limits and system settings

---

## Key Features

### 1. Screen Time Tracking

**What It Does:**
- Monitors when your child logs into their computer account
- Tracks total daily screen time in minutes
- Automatically locks the session when daily limit is reached

**How It Works:**
- Checks active user sessions every 60 seconds
- Records session start time, end time, and duration
- Enforces limits by locking the user session (requires login to resume)

**Viewing Screen Time:**
1. Go to **Dashboard** page
2. View "Today's Screen Time" section
3. Check the progress bar showing time used vs. limit

### 2. Browser Monitoring

**What It Does:**
- Tracks all websites visited in Firefox
- Records page titles, URLs, and visit timestamps
- Provides searchable browsing history

**How It Works:**
- Reads Firefox's history database every 5 minutes
- Stores sanitized history in EduGuard's database
- Does not track incognito/private browsing sessions

**Viewing Browsing History:**
1. Go to **History** page
2. Use date filters to narrow down the time range
3. Search for specific websites or keywords
4. Click on any entry to see full details

### 3. Content Filtering

**What It Does:**
- Blocks inappropriate websites using DNS-based filtering
- Uses both a static blocklist and AI-powered classification
- Logs all blocking attempts for parental review

**How It Works:**
1. **Static Blocklist**: Pre-defined list of known inappropriate domains
2. **AI Classification**: Unknown domains are analyzed by local LLM nightly
3. **DNS Blocking**: Blocked domains resolve to `0.0.0.0` via dnsmasq

**Categories Blocked:**
- Adult content
- Violence and weapons
- Gambling sites
- Social media (configurable)
- Known malware/phishing sites

**Viewing Blocked Attempts:**
1. Go to **Blocked** page
2. See list of blocked domains with timestamps
3. Review AI decisions and confidence scores
4. Override decisions if needed (see [Whitelisting Sites](#whitelisting-sites))

### 4. AI-Powered Insights

**What It Does:**
- Generates daily summaries of your child's online activity
- Identifies patterns and potential concerns
- Provides natural-language reports for parents

**How It Works:**
- Runs nightly at 8 PM (configurable)
- Analyzes day's browsing history and blocked attempts
- Uses local LLM (Ollama) to generate human-readable insights
- 100% private - no data leaves your computer

**Viewing Insights:**
1. Go to **Insights** page
2. Browse daily insight summaries
3. Read AI-generated behavior analysis
4. Check for flagged concerns or patterns

**Example Insight:**
```
Date: March 10, 2026

Activity Summary:
Your child spent 87 minutes online today, primarily focused on educational
content. They visited Khan Academy (23 minutes), Wikipedia (15 minutes),
and YouTube (educational videos, 30 minutes).

Notable Patterns:
- Increased interest in science topics (biology, chemistry)
- Consistent homework-related searches
- One blocked attempt: social media site during homework time

Recommendations:
Overall healthy online behavior. Continue encouraging educational exploration.
```

### 5. Automatic Enforcement

**What It Does:**
- Automatically locks computer when screen time limit is reached
- Prevents session access until next day (midnight reset)
- Cannot be bypassed without parent override

**How It Works:**
- Checks time usage every 60 seconds
- When limit exceeded, executes `loginctl lock-session`
- User must re-authenticate to unlock (but cannot use computer until limit resets)
- Parent can manually unlock via settings

**Manual Override:**
```bash
# Check current lock status
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT * FROM usage_sessions WHERE DATE(start_time) = DATE('now');"

# Temporarily increase limit for today
sudo nano /etc/eduguard/eduguard.yaml
# Change daily_screen_time value
sudo systemctl reload eduguard
```

---

## How-To Guides

### How to Adjust Screen Time Limits

**Via Dashboard (Recommended):**
1. Log into dashboard at `http://127.0.0.1:5000`
2. Go to **Settings** page
3. Find "Screen Time Limits" section
4. Adjust slider or enter minutes (e.g., 120 for 2 hours)
5. Click **Save Changes**
6. Changes take effect immediately

**Via Configuration File:**
```bash
# Edit config file
sudo nano /etc/eduguard/eduguard.yaml

# Find the limits section and modify:
limits:
  daily_screen_time: 120  # Change to desired minutes

# Reload daemon to apply changes
sudo systemctl reload eduguard
```

### How to Block Specific Websites

**Method 1: Add to Static Blocklist**
```bash
# Edit the blocklist
sudo nano /etc/eduguard/blocklist.txt

# Add domains, one per line:
example-bad-site.com
another-bad-site.com

# Reload the DNS configuration
sudo systemctl reload eduguard
```

**Method 2: Via Dashboard**
1. Go to **Settings** page
2. Find "Blocked Domains" section
3. Enter domain name (e.g., `example.com`)
4. Click **Add Domain**
5. Domain is immediately blocked

### How to Whitelist Sites

Sometimes the AI blocks educational or safe sites incorrectly. Here's how to allow them:

```bash
# Option 1: Remove from blocklist
sudo nano /etc/eduguard/blocklist.txt
# Delete the domain line
# Save and reload: sudo systemctl reload eduguard

# Option 2: Override AI decision in database
sudo sqlite3 /var/lib/eduguard/eduguard.db
sqlite> UPDATE ai_decisions SET decision='allow' WHERE domain='example.com';
sqlite> .quit
```

**Via Dashboard (if available):**
1. Go to **Blocked** page
2. Find the incorrectly blocked domain
3. Click **Allow** button next to it
4. Confirm the override

### How to Review Weekly Activity

1. Go to **Reports** page
2. Select date range (default: last 7 days)
3. View charts and statistics:
   - Daily screen time trend
   - Top 10 visited sites
   - Category breakdown (educational, entertainment, etc.)
   - Blocked attempts over time

4. Download report:
   - Click **Export CSV** for spreadsheet
   - Click **Export PDF** for printable report

### How to Check If System Is Working

**Quick Health Check:**
```bash
# 1. Check daemon is running
sudo systemctl status eduguard
# Should show: active (running)

# 2. Check Ollama is running (for AI features)
sudo systemctl status ollama
# Should show: active (running)

# 3. Check recent activity in logs
sudo tail -20 /var/log/eduguard/eduguard.log
# Should show recent job executions

# 4. Test DNS blocking
nslookup facebook.com
# Should return 0.0.0.0 if blocked

# 5. Check database has recent data
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT COUNT(*) FROM usage_sessions WHERE DATE(start_time) = DATE('now');"
# Should return number > 0 if child used computer today
```

### How to View Raw Logs

**Dashboard Logs:**
```bash
# View Flask dashboard logs
journalctl -u eduguard -f | grep dashboard
```

**Daemon Logs:**
```bash
# View all daemon activity
sudo tail -f /var/log/eduguard/eduguard.log

# View only errors
sudo grep ERROR /var/log/eduguard/eduguard.log

# View specific job logs
sudo grep "time_tracker" /var/log/eduguard/eduguard.log
sudo grep "browser_monitor" /var/log/eduguard/eduguard.log
sudo grep "ai_batch" /var/log/eduguard/eduguard.log
```

**Database Query Examples:**
```bash
# View today's usage
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT * FROM usage_sessions WHERE DATE(start_time) = DATE('now');"

# View recent browser visits
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT url, title, visited_at FROM browser_visits ORDER BY visited_at DESC LIMIT 10;"

# View AI decisions
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT domain, decision, reason, confidence FROM ai_decisions ORDER BY classified_at DESC LIMIT 10;"

# View recent blocked attempts
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT domain, blocked_at, reason FROM blocked_attempts WHERE DATE(blocked_at) = DATE('now');"
```

### How to Temporarily Disable Monitoring

**Disable for a few hours (manual mode):**
```bash
# Stop the daemon
sudo systemctl stop eduguard

# Resume monitoring later
sudo systemctl start eduguard
```

**Disable only certain features:**
```bash
# Edit config to disable specific monitoring
sudo nano /etc/eduguard/eduguard.yaml

# Disable browser monitoring:
browser:
  enabled: false  # Add this line

# Disable enforcement (tracking continues but no locking):
enforcer:
  enabled: false  # Add this line

# Reload to apply
sudo systemctl reload eduguard
```

### How to Reset Daily Limits (Emergency Override)

If you need to give your child more time in an emergency:

```bash
# Option 1: Manually reset today's usage to 0
sudo sqlite3 /var/lib/eduguard/eduguard.db "DELETE FROM usage_sessions WHERE DATE(start_time) = DATE('now');"

# Option 2: Temporarily increase limit to 8 hours
sudo nano /etc/eduguard/eduguard.yaml
# Change: daily_screen_time: 480
sudo systemctl reload eduguard

# Option 3: Unlock the session immediately
sudo loginctl unlock-session $(loginctl list-sessions | grep child-username | awk '{print $1}')
```

---

## Understanding AI Insights

### How the AI Works

**Local Processing:**
- EduGuard uses Ollama to run a small AI model (Llama 3.2 3B by default) **locally** on your computer
- No data is sent to cloud services or external APIs
- All analysis happens privately on your machine

**What It Analyzes:**
1. **Domain Classification**: Determines if unknown websites are appropriate
2. **Behavior Patterns**: Identifies trends in browsing habits
3. **Activity Summaries**: Generates daily reports in plain English
4. **Risk Assessment**: Flags potential concerns for parent review

**AI Decision Process:**
```
Unknown Website Visited
    ↓
Domain queued for classification
    ↓
Nightly batch job (2 AM)
    ↓
AI analyzes domain + context
    ↓
Decision: Allow / Block
    ↓
Reason + Confidence score stored
    ↓
Future visits use cached decision
```

### Reading AI Decisions

**Decision Format:**
```json
{
  "domain": "example-site.com",
  "decision": "block",
  "reason": "Social media platform that may distract from homework",
  "confidence": 0.85,
  "category": "social_media"
}
```

**Confidence Scores:**
- **0.9 - 1.0**: Very confident - trust this decision
- **0.7 - 0.9**: Confident - generally reliable
- **0.5 - 0.7**: Uncertain - review manually
- **< 0.5**: Low confidence - may need override

**Common Decision Reasons:**
- "Educational content suitable for children"
- "Adult content detected"
- "Social media platform"
- "Gaming site with user-generated content"
- "News website with potentially mature topics"
- "Online shopping not suitable for children"

### Overriding AI Decisions

If you disagree with an AI decision:

1. **Via Database (Advanced):**
   ```bash
   sudo sqlite3 /var/lib/eduguard/eduguard.db
   sqlite> UPDATE ai_decisions SET decision='allow', reason='Parent override: Educational resource' WHERE domain='example.com';
   sqlite> .quit
   ```

2. **Via Blocklist (Simpler):**
   ```bash
   # To allow: Remove from blocklist
   sudo nano /etc/eduguard/blocklist.txt

   # To block: Add to blocklist
   echo "example-site.com" | sudo tee -a /etc/eduguard/blocklist.txt
   sudo systemctl reload eduguard
   ```

---

## Troubleshooting Common Issues

### Dashboard Won't Load

**Symptom:** Cannot access `http://127.0.0.1:5000`

**Solutions:**
```bash
# Check if dashboard process is running
ps aux | grep eduguard-dashboard

# If not running, start it manually
eduguard-dashboard

# Check for port conflicts
sudo netstat -tulpn | grep :5000

# View dashboard errors
journalctl -u eduguard | grep dashboard
```

### Child's Activity Not Being Tracked

**Symptom:** Usage shows 0 minutes even though child is using computer

**Checks:**
```bash
# 1. Verify daemon is running
sudo systemctl status eduguard

# 2. Check if user session is being detected
loginctl list-sessions

# 3. View time tracker logs
sudo grep "time_tracker" /var/log/eduguard/eduguard.log | tail -10

# 4. Verify database is being updated
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT * FROM usage_sessions ORDER BY start_time DESC LIMIT 1;"
```

**Common Causes:**
- Wrong username in configuration
- Child using a different display server (e.g., Wayland instead of X11)
- Permissions issue with database

### Browser History Not Showing Up

**Symptom:** History page is empty or outdated

**Checks:**
```bash
# 1. Verify Firefox is installed
which firefox

# 2. Check Firefox profile path
ls ~/.mozilla/firefox/*/places.sqlite

# 3. Check browser monitor logs
sudo grep "browser_monitor" /var/log/eduguard/eduguard.log | tail -10

# 4. Verify history in database
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT COUNT(*) FROM browser_visits;"
```

**Solutions:**
```bash
# Update Firefox profile path in config
sudo nano /etc/eduguard/eduguard.yaml
# Correct: firefox_profile_path: /home/child-username/.mozilla/firefox

# Reload daemon
sudo systemctl reload eduguard
```

### Websites Not Being Blocked

**Symptom:** Child can access sites that should be blocked

**Checks:**
```bash
# 1. Verify dnsmasq is running
sudo systemctl status dnsmasq

# 2. Test DNS resolution
nslookup blocked-site.com
# Should return 0.0.0.0

# 3. Check if domain is in blocklist
sudo grep "blocked-site.com" /etc/eduguard/blocklist.txt

# 4. Check dnsmasq config
sudo cat /etc/dnsmasq.d/eduguard.conf
```

**Common Issues:**
- Child's computer not using dnsmasq for DNS (check `/etc/resolv.conf`)
- Domain not yet classified by AI (takes until next 2 AM batch)
- Child using a VPN or alternative DNS server

**Solution for Immediate Blocking:**
```bash
# Add to blocklist immediately
echo "site-to-block.com" | sudo tee -a /etc/eduguard/blocklist.txt

# Update dnsmasq config
sudo systemctl reload eduguard

# Verify it's blocked
nslookup site-to-block.com
```

### AI Insights Not Generating

**Symptom:** Insights page shows "No insights available"

**Checks:**
```bash
# 1. Verify Ollama is running
sudo systemctl status ollama

# 2. Check if model is downloaded
ollama list | grep llama

# 3. Test Ollama connection
curl http://localhost:11434/api/tags

# 4. Check AI batch job logs
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT * FROM job_runs WHERE job_name='ai_insights' ORDER BY started_at DESC LIMIT 5;"
```

**Solutions:**
```bash
# Download model if missing
ollama pull llama3.2:3b

# Restart Ollama
sudo systemctl restart ollama

# Manually trigger insights generation (test)
# Note: This is advanced, normally runs at 8 PM
```

### Session Locks Too Early or Late

**Symptom:** Child gets locked out before/after reaching the limit

**Checks:**
```bash
# Check current usage
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT username, SUM(duration_seconds)/60 as minutes FROM usage_sessions WHERE DATE(start_time) = DATE('now') GROUP BY username;"

# Check configured limit
sudo grep daily_screen_time /etc/eduguard/eduguard.yaml
```

**Adjustments:**
```bash
# Update limit if incorrect
sudo nano /etc/eduguard/eduguard.yaml
# Change: daily_screen_time: 120

# Reload daemon
sudo systemctl reload eduguard

# Unlock session if locked incorrectly
sudo loginctl unlock-session $(loginctl list-sessions | grep child-username | awk '{print $1}')
```

---

## Best Practices

### For Parents

**Daily Routine:**
1. **Morning**: Quick check of yesterday's AI insights
2. **Evening**: Review today's activity on dashboard (5 minutes)
3. **Weekly**: Generate and review weekly report
4. **Monthly**: Assess if screen time limits need adjustment

**Communication:**
- Be transparent with your child about monitoring
- Explain why certain sites are blocked
- Use insights as conversation starters, not punishment tools
- Adjust rules as child demonstrates responsibility

**Privacy Balance:**
- Focus on safety, not surveillance
- Don't obsess over every website visited
- Trust the AI for routine classification
- Review only flagged concerns in detail

**Limit Setting:**
- Start with conservative limits (1-2 hours/day)
- Increase gradually based on age and responsibility
- Consider separate limits for weekdays vs. weekends
- Allow extra time for legitimate homework needs

### For System Administrators

**Maintenance Schedule:**
```
Daily:   Check daemon status, review errors in logs
Weekly:  Review AI decision accuracy, update blocklist if needed
Monthly: Update Ollama and EduGuard, review disk usage
Yearly:  Full backup of database, security audit
```

**Backup Strategy:**
```bash
# Daily automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
sudo cp /var/lib/eduguard/eduguard.db /var/backups/eduguard-$DATE.db
sudo cp /etc/eduguard/eduguard.yaml /var/backups/eduguard-config-$DATE.yaml
# Keep only last 30 days
find /var/backups -name "eduguard-*.db" -mtime +30 -delete
```

**Security Hardening:**
```bash
# Restrict dashboard access to localhost only
sudo nano /etc/eduguard/eduguard.yaml
# Ensure: dashboard.host: 127.0.0.1

# Set strong parent password
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('strong-random-password'))"

# Secure sensitive files
sudo chmod 600 /etc/eduguard/env/eduguard.env
sudo chmod 600 /etc/eduguard/eduguard.yaml
sudo chown root:root /var/lib/eduguard/eduguard.db
```

**Monitoring Health:**
```bash
# Create a health check script
#!/bin/bash
echo "=== EduGuard Health Check ==="
echo "Daemon: $(systemctl is-active eduguard)"
echo "Ollama: $(systemctl is-active ollama)"
echo "Database: $([ -f /var/lib/eduguard/eduguard.db ] && echo 'OK' || echo 'MISSING')"
echo "Last session: $(sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT MAX(start_time) FROM usage_sessions;")"
echo "Recent errors: $(sudo grep -c ERROR /var/log/eduguard/eduguard.log)"
```

### Security Considerations

**What EduGuard Protects Against:**
- ✅ Excessive screen time
- ✅ Inappropriate website access
- ✅ Accidental exposure to harmful content
- ✅ Distraction during homework time

**What EduGuard Does NOT Protect Against:**
- ❌ VPN usage to bypass DNS filtering
- ❌ Incognito/private browsing mode
- ❌ Physical access to router to change DNS
- ❌ Creating a new user account
- ❌ Offline activities or apps

**Additional Protection Layers:**
1. Set BIOS password to prevent boot device changes
2. Disable guest account creation
3. Use router-level DNS filtering as backup
4. Physical supervision for young children
5. Open communication about online safety

---

## Getting Help

### Support Resources

**Documentation:**
- README.md - Quick overview
- INSTALL.md - Installation guide
- ARCHITECTURE.md - Technical details
- This file - Usage guide

**Logs and Diagnostics:**
```bash
# Generate diagnostic report
sudo journalctl -u eduguard -n 100 > eduguard-diag.txt
sudo tail -100 /var/log/eduguard/eduguard.log >> eduguard-diag.txt
sudo sqlite3 /var/lib/eduguard/eduguard.db ".schema" >> eduguard-diag.txt
```

**Community:**
- GitHub Issues: Report bugs or request features
- GitHub Discussions: Ask questions and share tips

**Before Asking for Help:**
1. Check this guide's troubleshooting section
2. Review logs for error messages
3. Verify all services are running (`systemctl status`)
4. Try restarting the daemon (`sudo systemctl restart eduguard`)
5. Check Ollama is working (`ollama list`)

---

## Appendix: Configuration Reference

### Complete Config File Example

```yaml
# /etc/eduguard/eduguard.yaml

# Database settings
database:
  path: /var/lib/eduguard/eduguard.db

# Screen time limits (in minutes)
limits:
  daily_screen_time: 120  # 2 hours
  warning_threshold: 15   # Warn when 15 minutes remain

# Browser monitoring
browser:
  firefox_profile_path: ~/.mozilla/firefox
  check_interval: 300  # 5 minutes
  enabled: true

# DNS and content filtering
dns:
  port: 53
  blocklist_path: /etc/eduguard/blocklist.txt
  dnsmasq_config: /etc/dnsmasq.d/eduguard.conf
  upstream_dns: 8.8.8.8

# AI classifier settings
ai:
  model: llama3.2:3b
  ollama_host: http://localhost:11434
  batch_interval: 86400  # 24 hours
  confidence_threshold: 0.7
  insights_time: "20:00"  # 8 PM

# Time tracking
tracking:
  poll_interval: 60  # 1 minute
  monitor_displays: [":0"]  # X11 displays to monitor

# Enforcement
enforcer:
  enabled: true
  check_interval: 60  # 1 minute
  lock_command: loginctl lock-session

# Dashboard settings
dashboard:
  host: 127.0.0.1
  port: 5000
  session_timeout: 3600  # 1 hour

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: /var/log/eduguard/eduguard.log
  max_size: 10485760  # 10 MB
  backup_count: 5
```

### Environment Variables

```bash
# /etc/eduguard/env/eduguard.env

# Flask secret for session encryption
FLASK_SECRET_KEY=your-random-secret-key-here

# Parent dashboard password (hashed)
PARENT_PASSWORD_HASH=scrypt:32768:8:1$...

# Optional: Custom config path
EDUGUARD_CONFIG=/etc/eduguard/eduguard.yaml

# Optional: Debug mode (never use in production)
# FLASK_DEBUG=1
```

---

**Last Updated:** March 2026
**Version:** 1.0.0
**For:** EduGuard Parental Control System
