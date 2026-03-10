# EduGuard

AI-powered parental control system for Edubuntu that enforces daily screen time limits, blocks age-inappropriate websites, and provides AI-powered activity reports using a local LLM.

## Quick Start

```bash
# Install Ollama (for local LLM)
curl -fsSL https://ollama.ai/install.sh | sh

# Download a small model (Llama 3.2 3B recommended)
ollama pull llama3.2:3b

# Install system dependencies
sudo apt install -y dnsmasq python3-pip python3-venv

# Install EduGuard
sudo pip install -e .

# Set up environment
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
- **AI Classification**: Local LLM via Ollama for intelligent content filtering (privacy-friendly, no API costs)
- **Parental Dashboard**: Web-based monitoring and configuration

## Documentation

See [INSTALL.md](INSTALL.md) for detailed installation and configuration instructions.

## Architecture

```
Child's Firefox → dnsmasq → static blocklist OR AI cache
                          → Local LLM via Ollama (nightly batch)

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
- Ollama with a small local LLM (Llama 3.2 3B, Mistral 7B, etc.)

## License

MIT License - see LICENSE file