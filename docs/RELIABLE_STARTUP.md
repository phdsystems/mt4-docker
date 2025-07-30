# Reliable MT4 Docker Startup Guide

This guide ensures MT4 Docker works correctly every time.

## Quick Start (Recommended)

Always use the quick start script from the project root:

```bash
cd /path/to/mt4-docker
./bin/quick_start.sh
```

This script automatically:
- ✓ Validates your .env file
- ✓ Checks for terminal.exe
- ✓ Stops any existing containers
- ✓ Builds with correct paths
- ✓ Starts with proper environment variables
- ✓ Verifies startup

## Manual Start (If Needed)

If you need to start manually, always use these exact commands:

```bash
# From project root directory
cd /path/to/mt4-docker

# Stop existing container
docker compose -f infra/docker/docker-compose.yml down

# Start with .env file
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d

# Verify
./bin/verify_startup.sh
```

## Essential Files

### 1. `.env` File (REQUIRED)
Must contain:
```
MT4_LOGIN=your_account_number
MT4_PASSWORD=your_password
MT4_SERVER=your_broker_server
VNC_PASSWORD=your_vnc_password
```

### 2. `terminal.exe` (REQUIRED)
Must be in project root directory.

## Verification Commands

### Check Everything is Working
```bash
./bin/verify_startup.sh
```

### Validate .env File
```bash
./bin/validate_env.sh
```

### Check Status
```bash
./bin/check_status.sh
```

### View Logs
```bash
./bin/view_logs.sh
```

## Common Issues and Solutions

### Issue: Environment variables not loaded
**Solution:**
```bash
# Always specify --env-file when using docker compose
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

### Issue: Container unhealthy
**Solution:**
```bash
# Restart with clean state
docker compose -f infra/docker/docker-compose.yml down
./bin/quick_start.sh
```

### Issue: Can't connect via VNC
**Solution:**
1. Check VNC is running: `./bin/verify_startup.sh`
2. Use correct password from .env file
3. Connect to: `localhost:5900`

### Issue: MT4 not starting
**Solution:**
1. Check credentials: `./bin/validate_env.sh`
2. Ensure terminal.exe is present
3. Check logs: `docker logs mt4-docker`

## Best Practices

1. **Always use scripts from project root**
   ```bash
   cd /path/to/mt4-docker
   ./bin/script_name.sh
   ```

2. **Use quick_start.sh for first time**
   - It handles all setup automatically
   - Validates everything before starting

3. **Keep .env file updated**
   - Run `./bin/validate_env.sh` after changes
   - Restart container after .env changes

4. **Monitor health**
   ```bash
   # Quick health check
   docker ps | grep mt4-docker
   
   # Detailed verification
   ./bin/verify_startup.sh
   ```

## Directory Structure
```
mt4-docker/
├── .env                    # Your credentials (create from .env.example)
├── terminal.exe            # MT4 executable (you provide this)
├── bin/
│   ├── quick_start.sh      # Use this to start
│   ├── verify_startup.sh   # Use this to verify
│   └── validate_env.sh     # Use this to check .env
└── infra/
    └── docker/
        └── docker-compose.yml  # Docker configuration
```

## Automated Startup (Optional)

To start MT4 Docker on system boot:

### Linux (systemd)
Create `/etc/systemd/system/mt4-docker.service`:
```ini
[Unit]
Description=MT4 Docker Trading Platform
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/mt4-docker
ExecStart=/usr/bin/docker compose -f infra/docker/docker-compose.yml --env-file .env up -d
ExecStop=/usr/bin/docker compose -f infra/docker/docker-compose.yml down

[Install]
WantedBy=multi-user.target
```

Enable with:
```bash
sudo systemctl enable mt4-docker.service
```

## Summary

For reliable operation every time:

1. Use `./bin/quick_start.sh` from project root
2. Keep .env file properly configured
3. Verify with `./bin/verify_startup.sh`
4. Monitor with `./bin/check_status.sh`

The scripts handle all the complexity - just run them from the project root directory!