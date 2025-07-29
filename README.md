# MT4 Docker Complete Setup

This is a complete, automated MT4 Docker setup with auto-compilation and deployment.

## Prerequisites

- Docker and Docker Compose installed
- MT4 terminal.exe file (see [GET_DEMO_MT4.md](GET_DEMO_MT4.md) for demo options)

## Quick Start

1. Copy your `terminal.exe` to this directory
2. Copy `.env.example` to `.env` and configure your account
3. Run: `./quick_start.sh`

For detailed setup instructions, see [SETUP.md](SETUP.md).
For troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
For VNC access guide, see [VNC_GUIDE.md](VNC_GUIDE.md).

## Features

- ✅ Fully automated setup
- ✅ Auto-compilation of EAs
- ✅ Auto-deployment of EAs
- ✅ Headless operation
- ✅ VNC access for debugging
- ✅ Monitoring scripts
- ✅ Health checks

## Scripts

- `quick_start.sh` - Build and start everything
- `check_status.sh` - Check system status
- `monitor.sh` - Real-time monitoring
- `deploy_ea.sh` - Deploy new EAs
- `connect_vnc.sh` - VNC connection
- `view_logs.sh` - View various logs
- `cleanup.sh` - Stop and cleanup

## Architecture

```
Container Services:
├── Xvfb (Virtual Display)
├── X11VNC (VNC Server)
├── Wine + MT4
└── Auto-compile monitor
```

## EA Auto-Deployment

The AutoDeploy_EA automatically:
- Loads on EURUSD H1 chart
- Writes status to files
- Updates every 30 seconds
- Logs all activity

## Monitoring

Check EA activity:
```bash
docker exec mt4-docker cat /mt4/MQL4/Files/ea_status.log
```

View logs:
```bash
./view_logs.sh
```

## Troubleshooting

If MT4 doesn't start:
1. Check terminal.exe is present
2. Verify Wine: `docker exec mt4-docker wine --version`
3. Check logs: `./view_logs.sh`
