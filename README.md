# MT4 Docker - Automated Trading Platform

A complete Dockerized MetaTrader 4 setup for automated trading with headless operation support.

## 📋 Prerequisites

- Docker and Docker Compose installed
- MT4 terminal.exe file (see [docs/guides/GET_DEMO_MT4.md](docs/guides/GET_DEMO_MT4.md))
- Trading account credentials

## 🚀 Quick Start

```bash
# 1. Copy your terminal.exe to project root
cp /path/to/terminal.exe .

# 2. Configure your account
cp .env.example .env
nano .env  # Add your credentials

# 3. Build and start
./bin/quick_start.sh
```

## 📁 Project Structure

```
mt4-docker/
├── bin/                    # Executable scripts
│   ├── quick_start.sh     # Build and start everything
│   ├── check_status.sh    # Check system status
│   ├── monitor.sh         # Real-time monitoring
│   ├── deploy_ea.sh       # Deploy new EAs
│   └── ...
├── config/                 # Configuration files
│   ├── docker/            # Docker configs
│   └── mt4/              # MT4 configs
├── docs/                   # Documentation
│   └── guides/           # Setup and usage guides
├── MQL4/                  # MT4 trading files
│   ├── Experts/          # Expert Advisors
│   ├── Indicators/       # Custom indicators
│   └── Scripts/          # Trading scripts
├── scripts/               # Internal scripts
└── logs/                  # Application logs
```

## 🔧 Common Operations

### Check Status
```bash
./bin/check_status.sh
```

### Deploy New EA
```bash
./bin/deploy_ea.sh YourEA.mq4
```

### Monitor in Real-time
```bash
./bin/monitor.sh
```

### View Logs
```bash
./bin/view_logs.sh
```

### Connect via VNC
```bash
./bin/connect_vnc.sh
# Server: localhost:5900
# Password: (from .env)
```

## 📚 Documentation

- [Setup Guide](docs/guides/SETUP.md) - Detailed installation instructions
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md) - Common issues and solutions
- [VNC Guide](docs/guides/VNC_GUIDE.md) - Remote access instructions
- [Get Demo MT4](docs/guides/GET_DEMO_MT4.md) - How to obtain MT4 terminal
- [EA Testing](docs/guides/EA_TESTING.md) - Automated EA testing framework
- [Market Data Streaming](docs/guides/MARKET_DATA_STREAMING.md) - Stream real-time market data

## 🤖 Automated Trading

Once configured, the system runs completely headless:
- Auto-compiles Expert Advisors
- Monitors trading activity
- Logs all operations
- Supports remote deployment

## 🧪 EA Testing Framework

Test your Expert Advisors with the built-in testing framework:

```bash
# Test the built-in EATester
./bin/test_ea.sh EATester ALL

# Test your own EA
./bin/test_ea.sh YourEA.mq4

# Run specific test suite
./bin/test_ea.sh EATester PERFORMANCE
```

Features:
- Unit testing for EA functions
- Integration testing
- Performance benchmarking
- Test report generation
- CI/CD integration ready

## 📊 Market Data Streaming

Stream real-time market data from MT4:

```bash
# Deploy market data streamer
./bin/deploy_market_streamer.sh

# Access via Python client
python3 clients/python/market_data_client.py

# Or via WebSocket
cd clients/nodejs && npm install && npm start
```

Streaming options:
- CSV file export
- Named pipe (low latency)
- WebSocket bridge
- Multiple symbol support
- Tick and bar data

## 🛡️ Security

- VNC password protected
- Resource limits enforced
- Isolated Docker environment
- No root access in container

## 📊 Resource Limits

- CPU: 2 cores max (0.5 reserved)
- Memory: 2GB max (512MB reserved)
- Configurable in docker-compose.yml

## 🔄 Maintenance

```bash
# Stop services
docker-compose down

# Clean up
./bin/cleanup.sh

# Update and restart
git pull
./bin/quick_start.sh
```

## ⚡ Quick Commands

| Command | Description |
|---------|-------------|
| `./bin/quick_start.sh` | Initial setup and start |
| `./bin/check_status.sh` | System health check |
| `./bin/monitor.sh` | Live monitoring |
| `./bin/deploy_ea.sh <file>` | Deploy new EA |
| `./bin/view_logs.sh` | View recent logs |
| `docker-compose restart` | Restart services |

## 🆘 Need Help?

1. Check [Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md)
2. Review logs with `./bin/view_logs.sh`
3. Run diagnostics: `./bin/master_diagnostic.sh`

---

**Note**: First-time setup requires VNC connection to configure broker server. Subsequent operations are fully headless.