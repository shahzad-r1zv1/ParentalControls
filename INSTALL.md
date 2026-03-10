# EduGuard - AI-Powered Parental Control System

![EduGuard Logo](https://via.placeholder.com/150x50?text=EduGuard)

EduGuard is a comprehensive parental control system designed for Edubuntu that enforces daily screen time limits, blocks age-inappropriate websites, and provides AI-powered activity reports through a local web dashboard using a local LLM.

## Features

### Core Functionality
- **Screen Time Tracking**: Monitors active user sessions and tracks daily screen time
- **Automatic Enforcement**: Locks user session when daily limits are exceeded
- **Browser Monitoring**: Tracks Firefox browsing history and visited sites
- **DNS-Based Content Filtering**: Blocks inappropriate domains via dnsmasq integration
- **AI-Powered Classification**: Uses local LLM via Ollama to intelligently classify unknown domains
- **Parental Dashboard**: Web-based interface for monitoring and configuration

### AI Integration
- Smart content classification beyond static blocklists using local LLM
- Natural-language behavior summaries for parents
- Daily activity insights and pattern detection
- Automatic batch processing of unclassified domains
- **Privacy-focused**: All AI processing happens locally, no data sent to external APIs
- **No API costs**: Free, unlimited usage

## Architecture

```
Child's Firefox → dnsmasq (port 53) → static blocklist OR AI classifier cache
                                    → unknown domain queue → Local LLM via Ollama (nightly batch)

EduGuard Daemon (root, systemd)
  ├── time_tracker    polls psutil every 60s, writes to SQLite
  ├── enforcer        calls loginctl lock-session when limits hit
  ├── browser_monitor copies + reads Firefox places.sqlite every 5 min
  └── scheduler       APScheduler (max_instances=1 on all jobs)

Flask Dashboard (127.0.0.1:5000, parent only, Flask-WTF CSRF)
  ├── reads SQLite for reports/insights
  └── writes eduguard.yaml + sends SIGUSR1 to daemon for hot-reload
```

## System Requirements

- **OS**: Edubuntu 22.04 LTS or later (Ubuntu-based distros)
- **Python**: 3.8 or later
- **Privileges**: Root access required for daemon
- **Dependencies**:
  - dnsmasq
  - systemd
  - Firefox browser
  - loginctl
  - Ollama with a small local LLM (Llama 3.2 3B, Mistral 7B, etc.)

## Installation

### 1. Install Ollama and Download a Model

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
sudo systemctl start ollama

# Download a small model (Llama 3.2 3B is recommended)
ollama pull llama3.2:3b

# Alternative: Use Mistral 7B (larger, more accurate but slower)
# ollama pull mistral:7b

# Verify model is downloaded
ollama list
```

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install -y dnsmasq python3-pip python3-venv
```

### 3. Install EduGuard

```bash
# Clone or download the repository
cd /opt
sudo git clone https://github.com/yourusername/eduguard.git
cd eduguard

# Create virtual environment
sudo python3 -m venv venv
sudo ./venv/bin/pip install -e .
```

### 4. Configure System Directories

```bash
# Create required directories
sudo mkdir -p /var/lib/eduguard
sudo mkdir -p /var/log/eduguard
sudo mkdir -p /etc/eduguard

# Copy configuration
sudo cp eduguard/config/eduguard.yaml /etc/eduguard/
sudo cp blocklist.txt /etc/eduguard/

# Set permissions
sudo chmod 755 /var/lib/eduguard
sudo chmod 755 /var/log/eduguard
sudo chmod 755 /etc/eduguard
```

### 5. Configure dnsmasq

```bash
# Create eduguard dnsmasq configuration
sudo mkdir -p /etc/dnsmasq.d

# Enable dnsmasq
sudo systemctl enable dnsmasq
sudo systemctl start dnsmasq
```

### 6. Set Environment Variables

```bash
# Set up Flask secret key and parent password
sudo mkdir -p /etc/eduguard/env
sudo bash -c 'cat > /etc/eduguard/env/eduguard.env << EOF
FLASK_SECRET_KEY=$(openssl rand -hex 32)
PARENT_PASSWORD_HASH=$(python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('parent123'))")
EOF'

# Secure the environment file
sudo chmod 600 /etc/eduguard/env/eduguard.env
```

### 7. Install systemd Service

```bash
# Copy service file
sudo cp eduguard.service /etc/systemd/system/

# Update service file to load environment
sudo sed -i '/\[Service\]/a EnvironmentFile=/etc/eduguard/env/eduguard.env' /etc/systemd/system/eduguard.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable eduguard
sudo systemctl start eduguard
```

### 8. Verify Installation

```bash
# Check Ollama is running
sudo systemctl status ollama

# Check daemon status
sudo systemctl status eduguard

# Check logs
sudo tail -f /var/log/eduguard/eduguard.log

# Test database
sudo sqlite3 /var/lib/eduguard/eduguard.db ".tables"
```

## Configuration

### Main Configuration File

Edit `/etc/eduguard/eduguard.yaml`:

```yaml
# Database settings
database:
  path: /var/lib/eduguard/eduguard.db

# Screen time limits (in minutes)
limits:
  daily_screen_time: 120  # 2 hours per day

# Browser monitoring
browser:
  firefox_profile_path: ~/.mozilla/firefox
  check_interval: 300  # 5 minutes

# DNS and content filtering
dns:
  port: 53
  blocklist_path: /etc/eduguard/blocklist.txt
  dnsmasq_config: /etc/dnsmasq.d/eduguard.conf

# AI classifier settings
ai:
  model: llama3.2:3b  # Small local model (or mistral:7b for more accuracy)
  ollama_host: http://localhost:11434  # Ollama API endpoint
  batch_interval: 86400  # 24 hours (nightly)
  confidence_threshold: 0.7

# Time tracking
tracking:
  poll_interval: 60  # 1 minute

# Dashboard settings
dashboard:
  host: 127.0.0.1
  port: 5000

# Logging
logging:
  level: INFO
  file: /var/log/eduguard/eduguard.log
```

### Blocklist Configuration

Edit `/etc/eduguard/blocklist.txt` to add domains to block:

```
# One domain per line
facebook.com
instagram.com
example-bad-site.com
```

### Hot-Reload Configuration

After modifying the configuration file, signal the daemon to reload:

```bash
sudo systemctl reload eduguard
# OR
sudo kill -USR1 $(cat /var/run/eduguard.pid)
```

## Running the Dashboard

The dashboard runs on localhost:5000 by default.

### Start Dashboard Manually

```bash
cd /opt/eduguard
sudo ./venv/bin/python3 -m eduguard.dashboard.app
```

### Access Dashboard

1. Open a browser on the local machine
2. Navigate to http://127.0.0.1:5000
3. Login with the parent password (default: `parent123`)

### Dashboard Features

- **Dashboard**: Overview of daily activity and statistics
- **History**: Browse child's web browsing history
- **Blocked**: View blocked access attempts
- **Insights**: AI-generated activity summaries
- **Reports**: Weekly activity reports and trends
- **Settings**: Configure screen time limits and system settings

## Usage

### For Parents

1. **Monitor Activity**: Check the dashboard daily for activity summaries
2. **Review AI Insights**: Read the AI-generated behavior summaries (generated at 8 PM daily)
3. **Adjust Limits**: Modify screen time limits through the Settings page
4. **Check Blocked Sites**: Review blocked attempts to understand what content was filtered

### For System Administrators

1. **View Logs**: `sudo journalctl -u eduguard -f`
2. **Check Database**: `sudo sqlite3 /var/lib/eduguard/eduguard.db`
3. **Update Blocklist**: Edit `/etc/eduguard/blocklist.txt` and reload
4. **Monitor Jobs**: Check job execution in the database `job_runs` table

## Database Schema

The system uses SQLite with the following tables:

- `usage_sessions`: Screen time tracking
- `browser_visits`: Firefox browsing history
- `blocked_attempts`: DNS blocking logs
- `ai_decisions`: AI classification cache
- `app_usage`: Application usage tracking
- `ai_insights`: Generated insights
- `config_audit`: Configuration change log
- `job_runs`: Scheduled job execution log
- `browser_history_cursor`: Browser sync state

## Scheduled Jobs

- **Time Tracking**: Every 60 seconds
- **Enforcer**: Every 60 seconds
- **Browser Monitor**: Every 5 minutes
- **DNS Update**: Every hour
- **AI Batch Classification**: Daily at 2 AM
- **AI Insights**: Daily at 8 PM
- **Daily Reset**: At midnight

## Security Considerations

1. **Root Privileges**: The daemon runs as root to access system functions
2. **Local Access Only**: Dashboard is bound to 127.0.0.1 (localhost)
3. **CSRF Protection**: Flask-WTF provides CSRF protection
4. **Password Protected**: Dashboard requires parent password
5. **Privacy-First AI**: All AI processing happens locally via Ollama, no data sent to external APIs
6. **SQLite WAL Mode**: Prevents database lock conflicts

## Local LLM Models

### Recommended Models

**Llama 3.2 3B** (Default, Recommended)
- Size: ~2GB
- Speed: Very fast
- Accuracy: Good for content classification
- Installation: `ollama pull llama3.2:3b`

**Mistral 7B**
- Size: ~4.1GB
- Speed: Moderate
- Accuracy: Excellent for nuanced decisions
- Installation: `ollama pull mistral:7b`

**Qwen2.5 3B**
- Size: ~2GB
- Speed: Very fast
- Accuracy: Good alternative to Llama
- Installation: `ollama pull qwen2.5:3b`

### Changing Models

Edit `/etc/eduguard/eduguard.yaml`:

```yaml
ai:
  model: mistral:7b  # Change to your preferred model
```

Then reload the daemon:
```bash
sudo systemctl reload eduguard
```

## Troubleshooting

### Ollama Not Running

```bash
# Check Ollama status
sudo systemctl status ollama

# Start Ollama if stopped
sudo systemctl start ollama
sudo systemctl enable ollama

# Test Ollama connection
curl http://localhost:11434/api/tags

# View Ollama logs
sudo journalctl -u ollama -n 50
```

### AI Classification Not Working

```bash
# Check if model is downloaded
ollama list

# Download model if missing
ollama pull llama3.2:3b

# Check Ollama connection in EduGuard logs
sudo grep -i "ollama" /var/log/eduguard/eduguard.log

# Check AI job logs
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT * FROM job_runs WHERE job_name='ai_batch' ORDER BY started_at DESC LIMIT 5;"

# Test Ollama manually
ollama run llama3.2:3b "Is example.com appropriate for children?"
```

### Model Too Slow

If your model is too slow, try a smaller model:

```bash
# Switch to a smaller model
ollama pull llama3.2:3b

# Or use an even smaller model
ollama pull tinyllama:1.1b  # Only 637MB

# Update config
sudo nano /etc/eduguard/eduguard.yaml
# Change model to: tinyllama:1.1b

# Reload daemon
sudo systemctl reload eduguard
```

### Daemon Won't Start

```bash
# Check logs
sudo journalctl -u eduguard -n 50

# Check permissions
ls -la /var/lib/eduguard
ls -la /var/log/eduguard

# Verify Python dependencies
/opt/eduguard/venv/bin/pip list

# Check if ollama library is installed
/opt/eduguard/venv/bin/pip show ollama
```

### Browser History Not Updating

```bash
# Check Firefox profile path
ls ~/.mozilla/firefox/*/places.sqlite

# Check browser monitor job
sudo sqlite3 /var/lib/eduguard/eduguard.db "SELECT * FROM job_runs WHERE job_name='browser_monitor' ORDER BY started_at DESC LIMIT 5;"
```

### DNS Blocking Not Working

```bash
# Check dnsmasq status
sudo systemctl status dnsmasq

# Check dnsmasq config
cat /etc/dnsmasq.d/eduguard.conf

# Test DNS resolution
nslookup blocked-domain.com
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop eduguard
sudo systemctl disable eduguard

# Remove service file
sudo rm /etc/systemd/system/eduguard.service
sudo systemctl daemon-reload

# Remove files (optional - keeps data)
sudo rm -rf /opt/eduguard
sudo rm -rf /etc/eduguard

# Remove data (WARNING: deletes all logs and history)
sudo rm -rf /var/lib/eduguard
sudo rm -rf /var/log/eduguard
```

## Development

### Running Tests

```bash
cd /opt/eduguard
./venv/bin/pytest tests/
```

### Development Mode

```bash
# Run daemon in foreground
sudo ./venv/bin/python3 -m eduguard.daemon.daemon

# Run dashboard with debug
FLASK_DEBUG=1 ./venv/bin/python3 -m eduguard.dashboard.app
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/eduguard/issues
- Documentation: https://github.com/yourusername/eduguard/wiki

## Acknowledgments

- Built with Flask, APScheduler, and Anthropic Claude
- Inspired by the need for safer online experiences for children
- Designed for the Edubuntu educational platform
