#!/bin/bash

echo "=== MT4 EA Status Check ==="
echo "Time: $(date)"
echo ""

# Check if MT4 is running
if docker exec mt4-docker pgrep -f terminal.exe > /dev/null; then
    echo "✓ MT4 Process: Running"
    
    # Get process info
    echo "  Process Info:"
    docker exec mt4-docker ps aux | grep terminal.exe | grep -v grep | awk '{print "    PID: "$2", CPU: "$3"%, MEM: "$4"%, Uptime: "$10}'
else
    echo "✗ MT4 Process: Not running"
fi

echo ""

# Check for Expert Advisors
echo "Expert Advisors Status:"
docker exec mt4-docker find /mt4/MQL4/Experts -name "*.ex4" -type f | while read ea; do
    ea_name=$(basename "$ea" .ex4)
    echo "  ✓ $ea_name - Compiled"
done

echo ""

# Check recent modifications
echo "Recent File Activity (last 10 minutes):"
docker exec mt4-docker find /mt4 -type f -mmin -10 ! -path "*/logs/*" | head -10 | while read file; do
    echo "  - $file"
done

echo ""

# Check if connected by looking for data files
echo "Connection Status:"
if docker exec mt4-docker find /mt4 -name "*.hst" -mmin -5 | grep -q .; then
    echo "  ✓ Receiving price data (history files updated)"
else
    echo "  ⚠ No recent price updates"
fi

echo ""

# Memory and disk usage
echo "Resource Usage:"
docker stats --no-stream mt4-docker | tail -1 | awk '{print "  CPU: "$3", Memory: "$4" / "$6", Net I/O: "$7" / "$9}'

echo ""
echo "To see live MT4 logs, check the Logs folder in MT4 Data Directory"
echo "To monitor in real-time: docker logs -f mt4-docker"