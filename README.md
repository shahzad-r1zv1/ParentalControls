# EduGuard - AI-Powered Parental Control System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-66%20passing-brightgreen.svg)](tests/)

**Keep your children safe online with intelligent, privacy-focused parental controls.**

EduGuard is a comprehensive parental control system for Linux (Edubuntu/Ubuntu) that enforces screen time limits, blocks inappropriate websites, and provides AI-powered activity insights—all processed locally on your computer with **zero cloud dependencies**.

---

## 🌟 Key Features

### ⏱️ Screen Time Management
- **Automatic tracking** of computer usage by session
- **Configurable daily limits** (default: 2 hours)
- **Automatic enforcement** - locks session when limit reached
- **Real-time monitoring** updated every minute

### 🛡️ Content Filtering
- **DNS-based blocking** via dnsmasq (cannot be bypassed by child)
- **Static blocklist** for known inappropriate sites
- **AI-powered classification** for unknown domains
- **Intelligent categorization** (educational, social media, adult content, etc.)

### 🤖 Local AI Intelligence
- **Privacy-first**: All AI processing happens on your computer
- **No API costs**: Use free local LLM via Ollama
- **Smart decisions**: Classifies content beyond simple keyword blocking
- **Daily insights**: Natural language summaries of online behavior

### 📊 Parental Dashboard
- **Web-based interface** accessible at http://127.0.0.1:5000
- **Real-time statistics** - screen time, blocked sites, activity trends
- **Browsing history** - complete Firefox history with search
- **AI insights** - daily behavior summaries and pattern detection
- **Easy configuration** - adjust limits and settings through UI

### 🔒 Security & Privacy
- **100% local processing** - no data sent to external servers
- **Root-level enforcement** - cannot be disabled by child user
- **Localhost-only dashboard** - no remote access
- **Password protected** - secure parent access
- **Comprehensive logging** - audit trail of all actions

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[INSTALL.md](INSTALL.md)** | Complete installation and setup guide |
| **[USER_GUIDE.md](USER_GUIDE.md)** | How-to guide for parents using EduGuard |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Technical documentation for developers |
| **[OLLAMA_MIGRATION.md](OLLAMA_MIGRATION.md)** | Guide for AI model setup and switching |

---

## 🚀 Quick Start

### Prerequisites

- **OS**: Ubuntu 22.04+ or Edubuntu (systemd-based)
- **Python**: 3.8 or later
- **Browser**: Firefox (for history monitoring)
- **Privileges**: Root/sudo access required

### 5-Minute Installation

```bash
# 1. Install Ollama (for local AI)
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Download a small AI model (2GB, ~3 minutes)
ollama pull llama3.2:3b

# 3. Install system dependencies
sudo apt update
sudo apt install -y dnsmasq python3-pip python3-venv

# 4. Clone and install EduGuard
git clone https://github.com/shahzad-r1zv1/ParentalControls.git
cd ParentalControls
sudo pip install -e .

# 5. Set up system directories
sudo mkdir -p /var/lib/eduguard /var/log/eduguard /etc/eduguard
sudo cp eduguard/config/eduguard.yaml /etc/eduguard/
sudo cp blocklist.txt /etc/eduguard/

# 6. Configure environment
sudo mkdir -p /etc/eduguard/env
sudo bash -c 'cat > /etc/eduguard/env/eduguard.env << EOF
FLASK_SECRET_KEY=$(openssl rand -hex 32)
PARENT_PASSWORD_HASH=$(python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('parent123'))")
EOF'

# 7. Install and start service
sudo cp eduguard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now eduguard

# 8. Verify it's running
sudo systemctl status eduguard
```

### Access the Dashboard

1. Open browser: http://127.0.0.1:5000
2. Login with default password: `parent123`
3. **Important**: Change password immediately in Settings

**⚠️ First-time setup tip**: Wait 5 minutes after installation for the first data collection cycle to complete.

---

## 🎯 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Child's Activity                          │
│                                                              │
│  Firefox Browser ──▶ Visits website                         │
│         │                                                    │
│         ▼                                                    │
│  DNS Query ──▶ dnsmasq (Port 53)                           │
│         │                                                    │
│         ├─▶ Static Blocklist ──▶ BLOCK if found            │
│         ├─▶ AI Cache ──▶ BLOCK if classified              │
│         └─▶ Allow ──▶ Queue for AI classification          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  EduGuard Daemon (Root)                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ TimeTracker  │  │   Enforcer   │  │BrowserMonitor│     │
│  │  Every 60s   │  │  Every 60s   │  │  Every 5min  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │               │
│         └────────┬────────┴────────┬────────┘               │
│                  ▼                 ▼                         │
│          SQLite Database    dnsmasq Config                   │
│                  │                                           │
│  ┌──────────────▼────────────────────────────────┐         │
│  │  AI Classifier (Nightly at 2 AM)              │         │
│  │  - Processes unclassified domains              │         │
│  │  - Local LLM via Ollama                        │         │
│  │  - Caches decisions in database                │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Parent Dashboard (127.0.0.1:5000)             │
│                                                              │
│  📊 Dashboard  │  📜 History  │  🚫 Blocked  │  💡 Insights│
│  ⚙️ Settings   │  📈 Reports  │                            │
└─────────────────────────────────────────────────────────────┘
```

### What Makes EduGuard Different?

✅ **100% Local AI** - Unlike competitors, no data ever leaves your computer
✅ **Zero Ongoing Costs** - No subscriptions, API fees, or cloud services
✅ **Privacy-Focused** - Your family's data stays in your family
✅ **Smart Classification** - AI understands context, not just keywords
✅ **Open Source** - Audit the code, customize as needed

---

## 📖 Usage Examples

### View Today's Activity

```bash
# Quick status check
sudo systemctl status eduguard

# View today's screen time
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT SUM(duration_seconds)/60 as minutes FROM usage_sessions
   WHERE DATE(start_time) = DATE('now');"

# View recent blocked sites
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT domain, blocked_at FROM blocked_attempts
   ORDER BY blocked_at DESC LIMIT 5;"
```

### Adjust Screen Time Limit

**Via Dashboard** (Recommended):
1. Go to Settings → Screen Time Limits
2. Adjust slider to desired hours/minutes
3. Click Save Changes

**Via Command Line**:
```bash
sudo nano /etc/eduguard/eduguard.yaml
# Change: daily_screen_time: 180  (3 hours)
sudo systemctl reload eduguard
```

### Block a Website Immediately

```bash
# Add to blocklist
echo "example-bad-site.com" | sudo tee -a /etc/eduguard/blocklist.txt

# Reload DNS configuration
sudo systemctl reload eduguard

# Verify it's blocked
nslookup example-bad-site.com
# Should return: 0.0.0.0
```

### View AI Insights

**Option 1**: Dashboard → Insights page
**Option 2**: Command line:
```bash
sudo sqlite3 /var/lib/eduguard/eduguard.db \
  "SELECT date, summary FROM ai_insights
   ORDER BY date DESC LIMIT 1;"
```

---

## 🧪 Testing

EduGuard includes a comprehensive test suite with **66 passing tests**:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=eduguard --cov-report=html tests/

# Test specific components
pytest tests/unit/test_ai_classifier.py -v
pytest tests/integration/ -v
```

**Test Coverage:**
- ✅ Database operations (9 tests)
- ✅ Time tracking (9 tests)
- ✅ Enforcement (11 tests)
- ✅ Browser monitoring (8 tests)
- ✅ DNS filtering (10 tests)
- ✅ AI classification (14 tests)
- ✅ Dashboard queries (5 tests)

---

## 🛠️ Configuration

### Main Configuration File

Located at `/etc/eduguard/eduguard.yaml`:

```yaml
# Screen time limits (in minutes)
limits:
  daily_screen_time: 120  # 2 hours per day

# Browser monitoring
browser:
  firefox_profile_path: ~/.mozilla/firefox
  check_interval: 300  # 5 minutes

# AI settings
ai:
  model: llama3.2:3b  # Local LLM model
  ollama_host: http://localhost:11434
  confidence_threshold: 0.7
  batch_interval: 86400  # Classify nightly

# Dashboard
dashboard:
  host: 127.0.0.1  # Localhost only
  port: 5000

# Logging
logging:
  level: INFO
  file: /var/log/eduguard/eduguard.log
```

### Environment Variables

Located at `/etc/eduguard/env/eduguard.env`:

```bash
FLASK_SECRET_KEY=your-random-secret-key
PARENT_PASSWORD_HASH=scrypt:32768:8:1$...
```

---

## 🔍 Troubleshooting

### Dashboard Won't Load

```bash
# Check if service is running
sudo systemctl status eduguard

# View logs
sudo journalctl -u eduguard -n 50

# Restart service
sudo systemctl restart eduguard
```

### AI Classification Not Working

```bash
# Check Ollama is running
sudo systemctl status ollama

# Test Ollama
ollama list
ollama run llama3.2:3b "Hello"

# Check EduGuard logs for Ollama errors
sudo grep -i ollama /var/log/eduguard/eduguard.log
```

### Browser History Not Updating

```bash
# Verify Firefox profile path
ls ~/.mozilla/firefox/*/places.sqlite

# Check browser monitor logs
sudo grep "browser_monitor" /var/log/eduguard/eduguard.log | tail -10
```

**For more troubleshooting**, see the [USER_GUIDE.md](USER_GUIDE.md#troubleshooting-common-issues).

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Development Setup:**
```bash
git clone https://github.com/shahzad-r1zv1/ParentalControls.git
cd ParentalControls
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install pytest pytest-cov pytest-mock
pytest tests/
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for personal or commercial purposes.

---

## 🙏 Acknowledgments

- **Ollama** - For making local LLMs accessible and easy to use
- **Llama 3.2** - Meta's efficient and capable language model
- **Flask** - Lightweight and powerful web framework
- **APScheduler** - Reliable job scheduling for Python
- **Edubuntu** - Educational Linux distribution inspiring this project

Built with ❤️ for families who value both safety and privacy.

---

## 📞 Support

- **Documentation**: See [docs](.) for detailed guides
- **Issues**: [GitHub Issues](https://github.com/shahzad-r1zv1/ParentalControls/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shahzad-r1zv1/ParentalControls/discussions)

---

## 🗺️ Roadmap

Future features under consideration:

- [ ] WhatsApp/Signal monitoring support
- [ ] Cross-browser support (Chrome, Edge)
- [ ] Mobile app for remote monitoring
- [ ] Weekly parent reports via email
- [ ] Multi-child support with separate profiles
- [ ] Application usage tracking (beyond browser)
- [ ] Screen time rewards system
- [ ] Content category customization per child
- [ ] Export/import configuration profiles

**Want to help?** Check out [CONTRIBUTING.md](CONTRIBUTING.md) or open an issue to discuss new features!

---

**Version**: 1.0.0
**Last Updated**: March 2026
**Tested On**: Ubuntu 22.04 LTS, Edubuntu 22.04 LTS