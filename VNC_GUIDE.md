# VNC Access Guide for MT4 Docker

## Overview
VNC (Virtual Network Computing) allows you to see and control the MT4 terminal running inside the Docker container. This is useful for:
- Initial MT4 login and setup
- Monitoring EA activity visually
- Debugging connection issues
- Managing charts and indicators

## Quick Connect

### Connection Details
```
Server: localhost:5900
Password: (from your .env file - VNC_PASSWORD)
```

### For Remote Access
```
Server: your-server-ip:5900
Password: (from your .env file - VNC_PASSWORD)
```

## VNC Client Installation

### Windows
Choose one of these clients:

1. **TightVNC** (Recommended - Free)
   - Download: https://www.tightvnc.com/download.php
   - Install TightVNC Viewer only (not the server)
   - Run TightVNC Viewer
   - Enter: `localhost:5900`

2. **RealVNC Viewer** (Free)
   - Download: https://www.realvnc.com/en/connect/download/viewer/
   - No registration required for viewer
   - Enter: `localhost:5900`

3. **UltraVNC**
   - Download: https://uvnc.com/downloads/ultravnc.html
   - Install viewer component
   - Enter: `localhost:5900`

### macOS
1. **Built-in Screen Sharing** (Easiest)
   - Open Finder
   - Press Cmd+K (or Go → Connect to Server)
   - Enter: `vnc://localhost:5900`
   - Enter password when prompted

2. **Alternative - TigerVNC**
   ```bash
   brew install tiger-vnc
   vncviewer localhost:5900
   ```

### Linux

1. **Remmina** (Usually pre-installed)
   ```bash
   # Install if needed
   sudo apt install remmina remmina-plugin-vnc
   
   # Run
   remmina
   ```
   - Create new connection
   - Protocol: VNC
   - Server: `localhost:5900`

2. **TigerVNC**
   ```bash
   # Install
   sudo apt install tigervnc-viewer
   
   # Connect
   vncviewer localhost:5900
   ```

3. **Command Line**
   ```bash
   # Using xvnc4viewer
   sudo apt install xvnc4viewer
   xvnc4viewer localhost:5900
   ```

## First Connection

1. **Start the container**
   ```bash
   docker compose up -d
   ```

2. **Wait for services to start**
   ```bash
   ./check_status.sh
   # Should show "MT4 is running"
   ```

3. **Connect with VNC client**
   - Open your VNC client
   - Enter server: `localhost:5900`
   - Enter password from `.env`

4. **What you should see**
   - MT4 terminal window
   - Login dialog (if not configured)
   - Charts loading (if logged in)

## Using VNC Effectively

### MT4 Login via VNC
1. If you see login dialog:
   - Enter your demo account number
   - Enter password
   - Select correct server from dropdown
   - Click "Login"

2. The credentials will be saved for future restarts

### Managing EAs
1. Open Navigator window (Ctrl+N if hidden)
2. Expand "Expert Advisors"
3. Drag EA onto a chart
4. Configure EA settings
5. Enable "AutoTrading" button

### Performance Tips
- VNC may feel slow - this is normal for Wine
- Use keyboard shortcuts when possible
- Minimize unnecessary chart animations
- Close unused windows in MT4

## Security Considerations

### Change Default Password
Edit `.env` file:
```bash
VNC_PASSWORD=your_secure_password_here
```

### Restrict Access
For production, limit VNC to localhost only:
```yaml
# In docker-compose.yml
ports:
  - "127.0.0.1:5900:5900"  # Local only
```

### Firewall Rules
If accessing remotely:
```bash
# Allow specific IP only
sudo ufw allow from 192.168.1.100 to any port 5900

# Or allow VNC from anywhere (less secure)
sudo ufw allow 5900/tcp
```

## Troubleshooting VNC

### Black Screen
- Wait 30-60 seconds for MT4 to start
- Check logs: `docker logs mt4-docker`

### Connection Refused
```bash
# Check VNC is running
docker exec mt4-docker ps aux | grep x11vnc

# Check port is mapped
docker port mt4-docker 5900
```

### Password Issues
```bash
# Verify password in .env
cat .env | grep VNC_PASSWORD

# Restart to apply changes
docker compose restart
```

### Slow Performance
- Normal for Wine applications
- Reduce MT4 visual effects
- Use lower color depth in VNC
- Close unnecessary MT4 windows

## Alternative: Headless Operation

Once MT4 is configured, you don't need VNC for daily operation:

1. **Monitor via logs**
   ```bash
   ./monitor.sh
   ./view_logs.sh
   ```

2. **Check EA status**
   ```bash
   docker exec mt4-docker cat /mt4/MQL4/Files/ea_status.log
   ```

3. **View trading activity**
   ```bash
   docker exec mt4-docker tail -f /mt4/MQL4/Logs/$(date +%Y%m%d).log
   ```

VNC is mainly needed for:
- Initial setup
- Troubleshooting
- Manual interventions
- Visual confirmation

## Quick Reference

| OS | Best VNC Client | Install Command |
|---|---|---|
| Windows | TightVNC | Download from website |
| macOS | Built-in | Finder → Cmd+K → vnc://localhost:5900 |
| Ubuntu | Remmina | Pre-installed |
| Linux | TigerVNC | `sudo apt install tigervnc-viewer` |

Connection: `localhost:5900` | Password: Check `.env` file