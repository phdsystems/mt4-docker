# Fix for "Bad EXE format" Error

## Problem
The current terminal.exe is a 64-bit executable, but MT4 requires a 32-bit version to run properly in Wine.

## Solution

You need to obtain a 32-bit MT4 terminal.exe. Here are your options:

### Option 1: Download 32-bit MT4 from your broker
1. Go to your broker's website (IG in this case)
2. Look for "MT4 Download" or "MetaTrader 4"
3. **Important**: Select Windows 32-bit version (not 64-bit)
4. Download and extract terminal.exe

### Option 2: Use a demo MT4 terminal (32-bit)
Many brokers provide 32-bit MT4 terminals. You can download a demo version and use your live credentials:
- IC Markets
- Pepperstone  
- XM
- Most other MT4 brokers

### How to verify you have the right version:
```bash
# In the container, check the file type
docker exec mt4-docker file /mt4/terminal.exe

# Should show: PE32 (not PE32+)
# Should show: Intel 80386 (not x86-64)
```

### Steps to fix:

1. Download a 32-bit MT4 terminal.exe
2. Replace the current one:
   ```bash
   cp /path/to/new/terminal.exe ./terminal.exe
   ```

3. Restart the container:
   ```bash
   docker compose -f infra/docker/docker-compose.yml restart
   ```

4. Verify it's working:
   ```bash
   ./bin/verify_startup.sh
   ```

## Why this happens
- Modern MT4 downloads are often 64-bit
- Wine in Docker is configured for 32-bit for better compatibility
- MT4 was originally a 32-bit application and many EAs expect 32-bit

## Prevention
Always download the 32-bit version of MT4 for Docker/Wine environments.