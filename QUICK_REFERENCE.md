# EduGuard Quick Reference

Quick command reference for parents and administrators.

---

## 🚀 Quick Start Commands

```bash
# Check if EduGuard is running
sudo systemctl status eduguard

# Start/Stop/Restart
sudo systemctl start eduguard
sudo systemctl stop eduguard
sudo systemctl restart eduguard

# View logs in real-time
sudo tail -f /var/log/eduguard/eduguard.log

# Access dashboard
http://127.0.0.1:5000
# Default password: parent123
```

---

## 📊 Daily Monitoring

### Check Today's Screen Time
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT SUM(duration_seconds)/60 as minutes
   FROM usage_sessions
   WHERE DATE(start_time) = DATE('now');"
```

### View Recent Browsing History
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT url, title, visited_at
   FROM browser_visits
   ORDER BY visited_at DESC LIMIT 10;"
```

### View Blocked Sites Today
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT domain, blocked_at, reason
   FROM blocked_attempts
   WHERE DATE(blocked_at) = DATE('now')
   ORDER BY blocked_at DESC;"
```

### View Latest AI Insight
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT date, summary
   FROM ai_insights
   ORDER BY date DESC LIMIT 1;"
```

---

## ⚙️ Configuration Changes

### Change Screen Time Limit
```bash
# Edit config file
sudo nano /etc/eduguard/eduguard.yaml
# Change: daily_screen_time: 180  (3 hours)

# Apply changes
sudo systemctl reload eduguard
```

### Block a Website
```bash
# Add to blocklist
echo "badsite.com" | sudo tee -a /etc/eduguard/blocklist.txt

# Reload
sudo systemctl reload eduguard

# Verify
nslookup badsite.com  # Should return 0.0.0.0
```

### Allow a Blocked Website
```bash
# Remove from blocklist
sudo nano /etc/eduguard/blocklist.txt
# Delete the line with the domain

# OR override AI decision
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "UPDATE ai_decisions SET decision='allow'
   WHERE domain='example.com';"

# Reload
sudo systemctl reload eduguard
```

### Change Parent Password
```bash
# Generate new password hash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-new-password'))"

# Update environment file
sudo nano /etc/eduguard/env/eduguard.env
# Replace PARENT_PASSWORD_HASH with new hash

# Restart
sudo systemctl restart eduguard
```

---

## 🤖 AI Model Management

### Check Ollama Status
```bash
sudo systemctl status ollama
ollama list
```

### Switch AI Model
```bash
# Download new model
ollama pull mistral:7b

# Update config
sudo nano /etc/eduguard/eduguard.yaml
# Change: model: mistral:7b

# Reload
sudo systemctl reload eduguard
```

### Test AI Classification
```bash
# Test Ollama directly
ollama run llama3.2:3b "Is youtube.com appropriate for children?"

# Check AI job logs
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT * FROM job_runs
   WHERE job_name='ai_batch'
   ORDER BY started_at DESC LIMIT 3;"
```

---

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check logs for errors
sudo journalctl -u eduguard -n 50

# Check permissions
ls -la /var/lib/eduguard
ls -la /var/log/eduguard

# Verify config syntax
python3 -c "import yaml; yaml.safe_load(open('/etc/eduguard/eduguard.yaml'))"
```

### Dashboard Won't Load
```bash
# Check if port 5000 is in use
sudo netstat -tulpn | grep :5000

# Check Flask secret is set
sudo cat /etc/eduguard/env/eduguard.env | grep FLASK_SECRET_KEY

# Restart service
sudo systemctl restart eduguard
```

### Browser History Not Updating
```bash
# Check Firefox profile path
ls ~/.mozilla/firefox/*/places.sqlite

# Check browser monitor job
sudo grep "browser_monitor" /var/log/eduguard/eduguard.log | tail -5

# Verify job is running
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT * FROM job_runs
   WHERE job_name='browser_monitor'
   ORDER BY started_at DESC LIMIT 3;"
```

### DNS Blocking Not Working
```bash
# Check dnsmasq status
sudo systemctl status dnsmasq

# Check dnsmasq config
cat /etc/dnsmasq.d/eduguard.conf

# Test DNS resolution
nslookup facebook.com  # Should return 0.0.0.0 if blocked

# Check system DNS
cat /etc/resolv.conf  # Should point to 127.0.0.1
```

### Ollama Not Responding
```bash
# Check Ollama service
sudo systemctl status ollama

# Test connection
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama

# Check if model is loaded
ollama list
```

---

## 📈 Reports & Analytics

### Weekly Screen Time Report
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT DATE(start_time) as date,
          SUM(duration_seconds)/60 as minutes
   FROM usage_sessions
   WHERE start_time >= date('now', '-7 days')
   GROUP BY DATE(start_time)
   ORDER BY date;"
```

### Top 10 Visited Sites
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT domain, COUNT(*) as visits
   FROM browser_visits
   WHERE visited_at >= datetime('now', '-7 days')
   GROUP BY domain
   ORDER BY visits DESC LIMIT 10;"
```

### Weekly Blocked Attempts
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT DATE(blocked_at) as date,
          COUNT(*) as blocks
   FROM blocked_attempts
   WHERE blocked_at >= date('now', '-7 days')
   GROUP BY DATE(blocked_at)
   ORDER BY date;"
```

### AI Decision Summary
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT decision, category, COUNT(*) as count
   FROM ai_decisions
   GROUP BY decision, category
   ORDER BY count DESC;"
```

---

## 🗄️ Database Maintenance

### Backup Database
```bash
# Create backup
sudo sqlite3 /var/lib/eduguard/eduguard.db ".backup '/tmp/eduguard-backup.db'"

# Or simple copy
sudo cp /var/lib/eduguard/eduguard.db /var/backups/eduguard-$(date +%Y%m%d).db
```

### Check Database Size
```bash
du -sh /var/lib/eduguard/eduguard.db
```

### Optimize Database
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db "VACUUM; ANALYZE; PRAGMA optimize;"
```

### Clean Old Data
```bash
# Delete usage older than 1 year
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "DELETE FROM usage_sessions
   WHERE start_time < date('now', '-1 year');"

# Delete browser history older than 6 months
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "DELETE FROM browser_visits
   WHERE visited_at < datetime('now', '-6 months');"
```

---

## 🔄 Emergency Controls

### Unlock Child Session Immediately
```bash
# Find session ID
loginctl list-sessions

# Unlock specific session
sudo loginctl unlock-session <session-id>
```

### Reset Today's Usage
```bash
# CAUTION: This clears today's tracking
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "DELETE FROM usage_sessions
   WHERE DATE(start_time) = DATE('now');"
```

### Temporarily Disable All Blocking
```bash
# Stop service
sudo systemctl stop eduguard

# Later, resume
sudo systemctl start eduguard
```

### Emergency Configuration Reset
```bash
# Restore default config
sudo cp /home/runner/work/ParentalControls/ParentalControls/eduguard/config/eduguard.yaml /etc/eduguard/

# Restart
sudo systemctl restart eduguard
```

---

## 📦 System Management

### Check All Job Status
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT job_name, status, started_at, completed_at
   FROM job_runs
   ORDER BY started_at DESC LIMIT 20;"
```

### View System Health
```bash
echo "=== EduGuard Health Check ==="
echo "Service: $(systemctl is-active eduguard)"
echo "Ollama: $(systemctl is-active ollama)"
echo "dnsmasq: $(systemctl is-active dnsmasq)"
echo "Database: $([ -f /var/lib/eduguard/eduguard.db ] && echo 'OK' || echo 'MISSING')"
echo "Config: $([ -f /etc/eduguard/eduguard.yaml ] && echo 'OK' || echo 'MISSING')"
```

### Update EduGuard
```bash
cd /opt/eduguard
sudo git pull
sudo pip install -e .
sudo systemctl restart eduguard
```

### Uninstall EduGuard
```bash
# Stop and disable
sudo systemctl stop eduguard
sudo systemctl disable eduguard

# Remove files
sudo rm /etc/systemd/system/eduguard.service
sudo systemctl daemon-reload

# Optionally remove data (WARNING: deletes all history)
# sudo rm -rf /var/lib/eduguard
# sudo rm -rf /var/log/eduguard
# sudo rm -rf /etc/eduguard
```

---

## 📞 Getting Help

### Generate Diagnostic Report
```bash
echo "=== EduGuard Diagnostic Report ===" > eduguard-diag.txt
echo "Date: $(date)" >> eduguard-diag.txt
echo "" >> eduguard-diag.txt

echo "=== Service Status ===" >> eduguard-diag.txt
systemctl status eduguard >> eduguard-diag.txt 2>&1
echo "" >> eduguard-diag.txt

echo "=== Recent Logs ===" >> eduguard-diag.txt
sudo tail -100 /var/log/eduguard/eduguard.log >> eduguard-diag.txt
echo "" >> eduguard-diag.txt

echo "=== Configuration ===" >> eduguard-diag.txt
sudo cat /etc/eduguard/eduguard.yaml >> eduguard-diag.txt
echo "" >> eduguard-diag.txt

echo "=== Database Tables ===" >> eduguard-diag.txt
sudo sqlite3 /var/lib/eduguard/eduguard.db ".schema" >> eduguard-diag.txt

echo "Report saved to: eduguard-diag.txt"
```

### Common Log Locations
```
/var/log/eduguard/eduguard.log  - Main daemon log
journalctl -u eduguard           - systemd service log
journalctl -u ollama             - Ollama service log
/var/log/syslog                  - System log (dnsmasq errors)
```

### Support Resources
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Installation**: [INSTALL.md](INSTALL.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **GitHub Issues**: https://github.com/shahzad-r1zv1/ParentalControls/issues

---

## 📝 Configuration File Locations

```
/etc/eduguard/eduguard.yaml           - Main configuration
/etc/eduguard/blocklist.txt           - Static blocklist
/etc/eduguard/env/eduguard.env        - Environment variables
/var/lib/eduguard/eduguard.db         - SQLite database
/var/log/eduguard/eduguard.log        - Application logs
/etc/dnsmasq.d/eduguard.conf          - DNS blocking config
/etc/systemd/system/eduguard.service  - systemd service file
```

---

## 🎯 Default Values

```yaml
Screen Time Limit:        120 minutes (2 hours)
Time Tracker Interval:    60 seconds
Enforcer Interval:        60 seconds
Browser Check Interval:   300 seconds (5 minutes)
DNS Update Interval:      3600 seconds (1 hour)
AI Batch Time:            02:00 (2 AM daily)
AI Insights Time:         20:00 (8 PM daily)
Dashboard Port:           5000
Dashboard Host:           127.0.0.1
Default Password:         parent123
AI Model:                 llama3.2:3b
AI Confidence Threshold:  0.7
```

---

**Version**: 1.0.0
**Last Updated**: March 2026
**For quick help**: Run `sudo systemctl status eduguard` and check logs
