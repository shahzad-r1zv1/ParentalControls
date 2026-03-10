# EduGuard

AI-powered parental control system for Edubuntu that enforces daily screen time limits, blocks age-inappropriate websites, and provides AI-powered activity reports.

## Quick Start

```bash
# Install dependencies
sudo apt install -y dnsmasq python3-pip python3-venv

# Install EduGuard
sudo pip install -e .

# Set up environment
export ANTHROPIC_API_KEY="your-api-key"
export FLASK_SECRET_KEY=$(openssl rand -hex 32)

# Run daemon
sudo eduguard-daemon

# Run dashboard (in another terminal)
eduguard-dashboard
```

Visit http://127.0.0.1:5000 (default password: `parent123`)

## Features

- **Screen Time Tracking**: Monitor and enforce daily screen time limits
- **Browser Monitoring**: Track Firefox browsing history
- **DNS Content Filtering**: Block inappropriate domains via dnsmasq
- **AI Classification**: Claude API for intelligent content filtering
- **Parental Dashboard**: Web-based monitoring and configuration

## Documentation

See [INSTALL.md](INSTALL.md) for detailed installation and configuration instructions.

## Architecture

```
Child's Firefox → dnsmasq → static blocklist OR AI cache
                          → Claude API (nightly batch)

EduGuard Daemon:
  ├── time_tracker    (polls every 60s)
  ├── enforcer        (locks session when limit hit)
  ├── browser_monitor (checks every 5 min)
  └── scheduler       (APScheduler)

Flask Dashboard (127.0.0.1:5000):
  ├── Activity reports and insights
  └── Configuration management
```

## Requirements

- Edubuntu 22.04+ or Ubuntu-based distro
- Python 3.8+
- dnsmasq, systemd, Firefox
- Anthropic API key (for AI features)

## License

MIT License - see LICENSE file