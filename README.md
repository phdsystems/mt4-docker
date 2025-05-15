# MT4 Docker Production v5.0

Complete, production-ready MT4 Docker environment with all fixes applied.

## Features

- ✅ Automated MT4 deployment
- ✅ Auto-compilation of EAs
- ✅ Network tools included
- ✅ Git Bash compatible
- ✅ VNC access for debugging
- ✅ Health monitoring
- ✅ Demo account setup helper
- ✅ Fixed COPY command issues

## Quick Start

1. Run the setup:
   ```bash
   ./quick_start.sh
   ```

2. Copy terminal.exe (if not already done):
   ```bash
   ./scripts/utilities/copy_terminal.sh
   ```

3. Configure credentials:
   ```bash
   ./scripts/utilities/setup_demo_account.sh
   ```

4. Monitor:
   ```bash
   ./scripts/utilities/monitor.sh
   ```

## Directory Structure

```
mt4-docker-production/
├── Dockerfile            # Fixed Dockerfile without COPY issues
├── docker-compose.yml    # Container orchestration
├── .env                 # Your MT4 credentials
├── config/              # MT4 configuration
├── MQL4/                # Trading files
│   ├── Experts/         # Expert Advisors
│   ├── Indicators/      # Custom indicators
│   └── Scripts/         # Trading scripts
├── logs/                # Application logs
├── scripts/
│   ├── troubleshooting/ # Diagnostic tools
│   └── utilities/       # Helper scripts
└── terminal.exe         # MT4 executable (you provide)
```

## Scripts

### Utilities
- `monitor.sh` - Real-time monitoring
- `copy_terminal.sh` - Copy terminal.exe to container
- `connect_vnc.sh` - VNC connection
- `deploy_ea.sh` - Deploy Expert Advisors
- `setup_demo_account.sh` - Configure demo account
- `view_logs.sh` - View logs
- `test_system.sh` - Test system components
- `cleanup.sh` - Docker cleanup

### Troubleshooting
- `master_diagnostic.sh` - Comprehensive system check

## Known Issues Fixed

1. **COPY command with wildcards** - Removed problematic COPY with wildcards
2. **Terminal.exe handling** - Now copied after container starts
3. **Dockerfile syntax** - Clean supervisor configuration
4. **Path issues** - Git Bash compatibility

## Demo Servers

Popular demo servers you can use:
- MetaQuotes-Demo
- ICMarkets-Demo02
- Pepperstone-Demo01
- XM.COM-Demo 3
- Exness-Demo

## Common Commands

```bash
# Check status
./scripts/troubleshooting/master_diagnostic.sh

# Monitor in real-time
./scripts/utilities/monitor.sh

# Deploy new EA
./scripts/utilities/deploy_ea.sh YourEA.mq4

# View logs
./scripts/utilities/view_logs.sh

# Connect via VNC
./scripts/utilities/connect_vnc.sh
```

## Support

1. Run diagnostic first
2. Check terminal.exe is copied
3. Verify credentials in .env
4. Check network connectivity
5. Monitor logs for errors

Version 5.0 - All issues fixed, production ready!
