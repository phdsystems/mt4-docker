#!/bin/bash

echo "MT4 Docker Service Check"
echo "======================="
echo ""

CONTAINER="mt4-docker"

# Check container
if ! docker ps | grep -q $CONTAINER; then
    echo "✗ Container not running"
    echo "  Run: docker-compose up -d"
    exit 1
fi

echo "✓ Container is running"
echo ""

# Check all services
echo "Service Status:"
echo "--------------"

# 1. Supervisor
echo -n "1. Supervisor:  "
if docker exec $CONTAINER test -S /var/run/supervisor.sock 2>/dev/null; then
    echo "✓ Socket exists"
    docker exec $CONTAINER supervisorctl status 2>/dev/null || echo "   But not responding"
else
    echo "✗ Socket missing"
    echo "   Checking process..."
    if docker exec $CONTAINER pgrep supervisord > /dev/null; then
        echo "   Process running but socket missing"
    else
        echo "   Process not running"
    fi
fi

# 2. Xvfb
echo -n "2. Xvfb:        "
if docker exec $CONTAINER pgrep Xvfb > /dev/null; then
    echo "✓ Running"
else
    echo "✗ Not running"
fi

# 3. x11vnc
echo -n "3. VNC Server:  "
if docker exec $CONTAINER pgrep x11vnc > /dev/null; then
    echo "✓ Running"
    echo "   Access via: vncviewer localhost:5900"
else
    echo "✗ Not running"
fi

# 4. Wine
echo -n "4. Wine:        "
docker exec $CONTAINER wine --version > /dev/null 2>&1 && echo "✓ Installed" || echo "✗ Not available"

# 5. Terminal.exe
echo -n "5. Terminal:    "
if docker exec $CONTAINER test -f /mt4/terminal.exe; then
    echo "✓ File exists"
    SIZE=$(docker exec $CONTAINER ls -lh /mt4/terminal.exe | awk '{print $5}')
    echo "   Size: $SIZE"
else
    echo "✗ File missing"
fi

# 6. MT4 Process
echo -n "6. MT4:         "
if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    echo "✓ Running"
    PID=$(docker exec $CONTAINER pgrep -f terminal.exe)
    echo "   PID: $PID"
else
    echo "✗ Not running"
fi

# Check configuration
echo ""
echo "Configuration:"
echo "-------------"
echo -n "Config file:    "
docker exec $CONTAINER test -f /mt4/config.ini && echo "✓ Exists" || echo "✗ Missing"

echo -n "Start script:   "
docker exec $CONTAINER test -f /mt4/start_mt4.sh && echo "✓ Exists" || echo "✗ Missing"

# Check EA
echo ""
echo "Expert Advisor:"
echo "--------------"
echo -n "EA source:      "
docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.mq4 && echo "✓ Exists" || echo "✗ Missing"

echo -n "EA compiled:    "
docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4 && echo "✓ Exists" || echo "✗ Missing"

echo -n "EA status:      "
if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log 2>/dev/null; then
    STATUS=$(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log 2>/dev/null)
    echo "$STATUS"
else
    echo "No status file"
fi

# Recommendations
echo ""
echo "Recommendations:"
echo "---------------"

if ! docker exec $CONTAINER pgrep supervisord > /dev/null; then
    echo "1. Supervisor not running. Try:"
    echo "   docker exec $CONTAINER /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf"
fi

if ! docker exec $CONTAINER pgrep Xvfb > /dev/null; then
    echo "2. Xvfb not running. Try:"
    echo "   docker exec $CONTAINER bash -c 'Xvfb :99 -screen 0 1024x768x16 &'"
fi

if ! docker exec $CONTAINER test -f /mt4/terminal.exe; then
    echo "3. Terminal.exe missing. Run:"
    echo "   ./scripts/utilities/copy_terminal_fixed.sh"
fi

if ! docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    echo "4. MT4 not running. After fixing above, run:"
    echo "   ./scripts/utilities/restart_services.sh"
fi

echo ""
echo "For manual debugging:"
echo "  docker exec -it $CONTAINER bash"
