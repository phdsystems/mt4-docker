# MT4 Docker Troubleshooting Guide

## Common Issues and Solutions

### 1. terminal.exe Not Found

**Error**: "ERROR: terminal.exe not found!"

**Solution**:
```bash
# Ensure terminal.exe is in the project root
ls -la terminal.exe

# Copy it if missing
cp /path/to/your/terminal.exe .
```

### 2. MT4 Won't Start

**Symptoms**: Container runs but MT4 doesn't start

**Debug Steps**:
```bash
# Check Wine installation
docker exec mt4-docker wine --version

# Check MT4 logs
docker exec mt4-docker tail -n 50 /mt4/logs/mt4_err.log

# Test Wine with simple command
docker exec mt4-docker wine cmd /c echo test
```

**Common Fixes**:
- Ensure terminal.exe is from a 32-bit MT4 installation
- Check file permissions: `chmod +x terminal.exe`
- Verify Wine environment: `docker exec mt4-docker env | grep WINE`

### 3. EA Not Compiling

**Symptoms**: .mq4 files present but no .ex4 files generated

**Debug Steps**:
```bash
# Check auto-compile logs
tail -f logs/auto_compile.log

# Manually trigger compilation
docker exec mt4-docker touch /mt4/MQL4/Experts/your_ea.mq4

# Check for compilation errors in MT4 logs
docker exec mt4-docker grep -i "error" /mt4/MQL4/Logs/*.log
```

### 4. VNC Connection Failed

**Error**: Cannot connect to VNC server

**Solutions**:
```bash
# Check if VNC is running
docker exec mt4-docker ps aux | grep x11vnc

# Check VNC logs
tail -f logs/x11vnc_err.log

# Verify port mapping
docker ps | grep 5900

# Test VNC port is accessible
docker port mt4-docker 5900
netstat -tuln | grep 5900
```

**VNC Client Options**:
If you don't have a VNC client, install one:

- **Windows**: 
  - Download TightVNC from [tightvnc.com](https://www.tightvnc.com/download.php)
  - Or RealVNC Viewer from [realvnc.com](https://www.realvnc.com/en/connect/download/viewer/)

- **macOS**: 
  - Use built-in Screen Sharing: Finder → Go → Connect to Server → `vnc://localhost:5900`
  - Or install: `brew install tiger-vnc`

- **Linux**: 
  ```bash
  # Ubuntu/Debian
  sudo apt install remmina remmina-plugin-vnc
  # Or
  sudo apt install tigervnc-viewer
  ```

**Connection String Format**:
```
Server: localhost:5900
Password: (check your .env file for VNC_PASSWORD)
```

**Common VNC Issues**:
- **Black screen**: MT4 might be starting, wait 30 seconds
- **Password rejected**: Check `.env` file has correct VNC_PASSWORD
- **Connection refused**: Ensure port 5900 is not blocked by firewall
- **Slow response**: Normal for Wine applications, be patient

### 5. High CPU/Memory Usage

**Symptoms**: Container using excessive resources

**Solutions**:
```bash
# Check resource usage
docker stats mt4-docker

# Adjust limits in docker-compose.yml
# Reduce CPU: cpus: '1'
# Reduce memory: memory: 1G

# Restart with new limits
docker-compose down
docker-compose up -d
```

### 6. MT4 Login Failed

**Error**: Cannot connect to trading server

**Debug Steps**:
```bash
# Verify credentials in .env
cat .env | grep MT4_

# Check server connectivity
docker exec mt4-docker ping -c 4 8.8.8.8

# Verify server name is correct
# Common formats: "Demo-Server", "Live-Server", "ICMarkets-Demo01"
```

### 7. Persistent Crashes

**Symptoms**: MT4 keeps restarting

**Debug Process**:
```bash
# Check all logs
./view_logs.sh

# Monitor in real-time
docker logs -f mt4-docker

# Run interactively for debugging
docker-compose down
docker run -it --rm \
  -e DISPLAY=:99 \
  -v $(pwd)/MQL4:/mt4/MQL4 \
  mt4-docker \
  /bin/bash
```

### 8. File Permission Issues

**Error**: Cannot write to MQL4/Files directory

**Fix**:
```bash
# Fix permissions
sudo chown -R $(whoami):$(whoami) MQL4/
chmod -R 755 MQL4/
```

## Advanced Debugging

### Enable Wine Debug Output
```bash
# Edit docker-compose.yml, add to environment:
- WINEDEBUG=+all

# Restart and check logs
docker-compose restart
docker logs mt4-docker
```

### Manual MT4 Start
```bash
# Enter container
docker exec -it mt4-docker /bin/bash

# Start X server
Xvfb :99 -screen 0 1024x768x16 &

# Start MT4 manually
DISPLAY=:99 wine terminal.exe
```

### Check Core Dumps
```bash
# If MT4 crashes, check for core dumps
docker exec mt4-docker ls -la /tmp/*.dmp
```

## Getting Help

If issues persist:

1. Collect diagnostic information:
   ```bash
   ./master_diagnostic.sh > diagnostic.log
   ```

2. Check logs:
   - `/mt4/logs/mt4_err.log` - MT4 errors
   - `/mt4/logs/supervisord.log` - Process manager
   - `/mt4/MQL4/Logs/` - MT4 internal logs

3. Verify your setup:
   - Docker version: `docker --version`
   - Docker Compose version: `docker-compose --version`
   - Host OS: `uname -a`

4. Common fixes to try:
   - Rebuild image: `docker-compose build --no-cache`
   - Reset volumes: `docker-compose down -v`
   - Update Wine: Rebuild with latest base image