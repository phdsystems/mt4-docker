# MT4 Docker Setup Guide

## Prerequisites

1. Docker and Docker Compose installed on your system
2. MT4 terminal.exe file from your broker
3. MT4 account credentials (login, password, server)

## Initial Setup

### 1. Prepare Environment

```bash
# Clone or download this repository
cd mt4-docker

# Copy your MT4 terminal.exe to this directory
cp /path/to/your/terminal.exe .

# Create .env file from template
cp .env.example .env

# Edit .env with your MT4 credentials
nano .env
```

### 2. Configure MT4 Account

Edit the `.env` file with your MT4 account details:

```env
MT4_LOGIN=12345678         # Your MT4 account number
MT4_PASSWORD=yourpassword  # Your MT4 password
MT4_SERVER=Demo-Server     # Your broker's server name
VNC_PASSWORD=securevnc123  # Password for VNC access (optional)
```

### 3. Build and Start

```bash
# Make scripts executable
chmod +x *.sh

# Quick start (builds and runs everything)
./quick_start.sh

# Or manually:
docker-compose build
docker-compose up -d
```

## Monitoring and Management

### Check Status
```bash
# View system status
./check_status.sh

# Real-time monitoring
./monitor.sh

# View logs
./view_logs.sh
```

### VNC Access
Connect to the MT4 interface via VNC to see and control MT4 visually:

#### Compatible VNC Clients
You can use any of these VNC clients:
- **RealVNC Viewer** - [realvnc.com](https://www.realvnc.com/en/connect/download/viewer/)
- **TightVNC** - [tightvnc.com](https://www.tightvnc.com/download.php)
- **TigerVNC** - [tigervnc.org](https://tigervnc.org/)
- **UltraVNC** - [uvnc.com](https://uvnc.com/downloads/)
- **macOS Screen Sharing** - Built into macOS (Cmd+K in Finder)
- **Remmina** - Linux default (pre-installed on Ubuntu/Debian)

#### Connection Details
```bash
Server: localhost:5900
Password: (your VNC_PASSWORD from .env)
```

#### Using the Helper Script
```bash
# If you have a VNC viewer installed:
./connect_vnc.sh
```

#### Manual Connection
1. Open your VNC client
2. Enter server address: `localhost:5900` (or `your-server-ip:5900` for remote)
3. Enter password from your `.env` file
4. You should see MT4 running in a virtual display

### Deploy New EAs
```bash
# Copy EA to MQL4/Experts directory
cp your_ea.mq4 MQL4/Experts/

# Deploy and compile
./deploy_ea.sh
```

## File Structure

```
mt4-docker/
├── MQL4/                  # MT4 data directory (shared with container)
│   ├── Experts/          # Expert Advisors
│   ├── Indicators/       # Custom indicators
│   ├── Scripts/          # Scripts
│   └── Files/           # EA output files
├── logs/                 # Application logs
├── config/              # MT4 configuration files
└── terminal.exe         # Your MT4 terminal executable
```

## Common Operations

### Stop Services
```bash
docker-compose down
```

### View EA Status
```bash
docker exec mt4-docker cat /mt4/MQL4/Files/ea_status.log
```

### Restart Services
```bash
docker-compose restart
```

### Clean Up
```bash
./cleanup.sh
```

## Resource Limits

The container is configured with the following limits:
- CPU: 2 cores maximum, 0.5 cores reserved
- Memory: 2GB maximum, 512MB reserved

Adjust these in `docker-compose.yml` if needed.

## Security Notes

1. VNC is password-protected by default
2. Store credentials securely in `.env` file
3. Never commit `.env` file to version control
4. Consider using Docker secrets for production deployments

## Next Steps

1. Monitor EA activity in `logs/` directory
2. Check `MQL4/Files/` for EA output
3. Use VNC to visually verify MT4 is running correctly
4. Deploy your custom EAs using the deploy script