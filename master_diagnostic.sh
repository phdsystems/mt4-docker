#!/bin/bash

# Master MT4 Docker Diagnostic Script
# Comprehensive troubleshooting and auto-fixing

CONTAINER="mt4-docker"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Print functions
print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo "MT4 Docker Master Diagnostic Tool"
echo "================================"
echo "$(date)"
echo ""

# 1. Container Status
print_header "1. Container Status"
if docker ps | grep -q $CONTAINER; then
    print_success "Container is running"
    CONTAINER_ID=$(docker ps | grep $CONTAINER | awk '{print $1}')
    echo "Container ID: $CONTAINER_ID"
    echo "Uptime: $(docker ps | grep $CONTAINER | awk '{print $4,$5,$6}')"
else
    print_error "Container is not running"
    echo "Attempting to start..."
    docker-compose up -d
    sleep 10
fi
echo ""

# 2. Process Status
print_header "2. Process Status"
echo "Checking processes..."

# Xvfb
if docker exec $CONTAINER pgrep -f Xvfb > /dev/null; then
    print_success "Xvfb (Virtual Display) is running"
else
    print_error "Xvfb is not running"
fi

# X11VNC
if docker exec $CONTAINER pgrep -f x11vnc > /dev/null; then
    print_success "X11VNC is running"
else
    print_warning "X11VNC is not running (VNC access unavailable)"
fi

# MT4
if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    print_success "MT4 is running"
    MT4_PID=$(docker exec $CONTAINER pgrep -f terminal.exe)
    echo "  PID: $MT4_PID"
else
    print_error "MT4 is not running"
fi
echo ""

# 3. Wine Environment
print_header "3. Wine Environment"
WINE_VERSION=$(docker exec $CONTAINER wine --version 2>/dev/null)
echo "Wine version: $WINE_VERSION"
echo "WINEARCH: $(docker exec $CONTAINER bash -c 'echo $WINEARCH')"
echo "DISPLAY: $(docker exec $CONTAINER bash -c 'echo $DISPLAY')"

# Test Wine functionality
if docker exec $CONTAINER wine cmd /c echo "test" > /dev/null 2>&1; then
    print_success "Wine is functional"
else
    print_error "Wine test failed"
fi
echo ""

# 4. MT4 File Structure
print_header "4. MT4 File Structure"
echo "Checking MT4 directories..."

# Check critical directories
DIRS=("/mt4" "/mt4/MQL4" "/mt4/MQL4/Experts" "/mt4/MQL4/Files" "/mt4/MQL4/Logs")
for dir in "${DIRS[@]}"; do
    if docker exec $CONTAINER test -d "$dir"; then
        print_success "$dir exists"
    else
        print_error "$dir missing"
        docker exec $CONTAINER mkdir -p "$dir"
    fi
done

# Check terminal.exe
if docker exec $CONTAINER test -f /mt4/terminal.exe; then
    print_success "terminal.exe found"
    echo "  Size: $(docker exec $CONTAINER ls -lh /mt4/terminal.exe | awk '{print $5}')"
else
    print_error "terminal.exe missing!"
    echo "  Please copy terminal.exe to the container"
fi
echo ""

# 5. EA Files
print_header "5. Expert Advisor Files"
echo "Checking EA files..."

# Check source file
if docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.mq4; then
    print_success "AutoDeploy_EA.mq4 exists"
    echo "  Modified: $(docker exec $CONTAINER stat -c %y /mt4/MQL4/Experts/AutoDeploy_EA.mq4)"
else
    print_error "AutoDeploy_EA.mq4 missing"
    echo "  Creating EA file..."
    
    docker exec $CONTAINER bash -c 'cat > /mt4/MQL4/Experts/AutoDeploy_EA.mq4 << "EOF"
//+------------------------------------------------------------------+
//|                                              AutoDeploy_EA.mq4   |
//+------------------------------------------------------------------+
#property copyright "Auto-Deploy EA"
#property version   "1.00"
#property strict

int OnInit() {
    Print("AutoDeploy EA Started at " + TimeToStr(TimeCurrent()));
    CreateFile("ea_status.log", "EA INITIALIZED");
    EventSetTimer(30);
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
    EventKillTimer();
    CreateFile("ea_status.log", "EA STOPPED");
}

void OnTimer() {
    CreateFile("ea_status.log", "RUNNING - " + TimeToStr(TimeCurrent()));
    Print("Heartbeat: " + TimeToStr(TimeCurrent()));
}

void OnTick() {
    static datetime lastLog = 0;
    if(TimeCurrent() - lastLog > 60) {
        lastLog = TimeCurrent();
        CreateFile("ea_activity.log", "Tick at " + TimeToStr(TimeCurrent()));
    }
    Comment("AutoDeploy EA\n" + TimeToStr(TimeCurrent()) + "\nBid: " + DoubleToStr(Bid, Digits));
}

void CreateFile(string filename, string content) {
    int handle = FileOpen(filename, FILE_WRITE|FILE_TXT);
    if(handle != INVALID_HANDLE) {
        FileWriteString(handle, content);
        FileClose(handle);
    }
}
//+------------------------------------------------------------------+
EOF'
    print_success "EA file created"
fi

# Check compiled file
if docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4; then
    print_success "AutoDeploy_EA.ex4 (compiled) exists"
else
    print_warning "AutoDeploy_EA.ex4 not found (not compiled yet)"
fi
echo ""

# 6. Compilation Attempt
print_header "6. Compilation Attempt"
echo "Triggering EA compilation..."

# Touch the file to trigger compilation
docker exec $CONTAINER touch /mt4/MQL4/Experts/AutoDeploy_EA.mq4

# Restart MT4 to force compilation
echo "Restarting MT4..."
docker exec $CONTAINER pkill -f terminal.exe || true
sleep 5

# Wait for MT4 to restart
for i in {1..10}; do
    if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
        print_success "MT4 restarted"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Wait for compilation
echo "Waiting for compilation (30 seconds)..."
for i in {1..6}; do
    if docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4; then
        print_success "EA compiled successfully!"
        break
    fi
    echo -n "."
    sleep 5
done
echo ""

# 7. EA Activity
print_header "7. EA Activity Check"
if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log; then
    print_success "EA status log found"
    echo "  Content: $(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log)"
else
    print_warning "No EA status log yet"
fi

if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_activity.log; then
    print_success "EA activity log found"
    echo "  Last entry: $(docker exec $CONTAINER tail -1 /mt4/MQL4/Files/ea_activity.log)"
else
    print_warning "No EA activity log yet"
fi
echo ""

# 8. MT4 Login and Connection Test
print_header "8. MT4 Login and Connection Test"

# Check environment variables
echo "Checking credentials from environment..."
MT4_LOGIN=$(docker exec $CONTAINER bash -c 'echo $MT4_LOGIN')
MT4_SERVER=$(docker exec $CONTAINER bash -c 'echo $MT4_SERVER')

if [ -z "$MT4_LOGIN" ] || [ "$MT4_LOGIN" = "your_demo_account" ]; then
    print_error "MT4_LOGIN not configured (current: $MT4_LOGIN)"
    echo "  Please update .env file with valid credentials"
else
    print_success "MT4_LOGIN is set: $MT4_LOGIN"
fi

if [ -z "$MT4_SERVER" ] || [ "$MT4_SERVER" = "your_broker_server" ]; then
    print_error "MT4_SERVER not configured (current: $MT4_SERVER)"
    echo "  Please update .env file with valid server"
else
    print_success "MT4_SERVER is set: $MT4_SERVER"
fi

# Check configuration file
echo ""
echo "Checking MT4 configuration..."
if docker exec $CONTAINER test -f /mt4/config.ini; then
    print_success "config.ini exists"
    echo "Login setting in config:"
    docker exec $CONTAINER grep -i "login\|server" /mt4/config.ini | head -5
else
    print_error "config.ini missing"
fi

# Check connection status in logs
echo ""
echo "Checking connection status in logs..."
CONNECTION_LOG=$(docker exec $CONTAINER find /mt4 -name "*.log" -exec grep -l "connect\|login\|author" {} \; 2>/dev/null | head -1)

if [ ! -z "$CONNECTION_LOG" ]; then
    echo "Found connection info in: $CONNECTION_LOG"
    echo "Recent connection messages:"
    docker exec $CONTAINER grep -i "connect\|login\|author" "$CONNECTION_LOG" | tail -5
    
    # Check for successful login
    if docker exec $CONTAINER grep -i "login.*success\|author.*success" "$CONNECTION_LOG" > /dev/null 2>&1; then
        print_success "Login appears successful"
    else
        print_warning "No successful login found in logs"
    fi
else
    print_warning "No connection logs found"
fi

# Test creating a simple connection test EA
echo ""
echo "Creating connection test EA..."
docker exec $CONTAINER bash -c 'cat > /mt4/MQL4/Scripts/test_connection.mq4 << "EOF"
//+------------------------------------------------------------------+
//|                                           test_connection.mq4    |
//+------------------------------------------------------------------+
#property copyright "Connection Test"
#property version   "1.00"
#property strict

void OnStart() {
    Print("Connection Test Starting...");
    
    // Check account info
    if(AccountNumber() > 0) {
        Print("Account Number: ", AccountNumber());
        Print("Account Name: ", AccountName());
        Print("Account Server: ", AccountServer());
        Print("Account Company: ", AccountCompany());
        Print("Account Currency: ", AccountCurrency());
        Print("Account Balance: ", AccountBalance());
        Print("Connection Status: CONNECTED");
        
        // Write to file
        int handle = FileOpen("connection_test.log", FILE_WRITE|FILE_TXT);
        if(handle != INVALID_HANDLE) {
            FileWriteString(handle, "CONNECTED - Account: " + IntegerToString(AccountNumber()));
            FileClose(handle);
        }
    } else {
        Print("Connection Status: NOT CONNECTED");
        Print("Account Number is 0 - Not logged in");
        
        // Write to file
        int handle = FileOpen("connection_test.log", FILE_WRITE|FILE_TXT);
        if(handle != INVALID_HANDLE) {
            FileWriteString(handle, "NOT CONNECTED");
            FileClose(handle);
        }
    }
}
//+------------------------------------------------------------------+
EOF'

# Touch to trigger compilation
docker exec $CONTAINER touch /mt4/MQL4/Scripts/test_connection.mq4

# Wait a moment
sleep 5

# Check if connection test ran
if docker exec $CONTAINER test -f /mt4/MQL4/Files/connection_test.log; then
    CONNECTION_STATUS=$(docker exec $CONTAINER cat /mt4/MQL4/Files/connection_test.log)
    echo ""
    echo "Connection test result: $CONNECTION_STATUS"
    
    if [[ "$CONNECTION_STATUS" == *"CONNECTED"* ]]; then
        print_success "MT4 is connected to trading server"
    else
        print_error "MT4 is NOT connected to trading server"
        echo "  This prevents EA compilation!"
    fi
else
    print_warning "Connection test did not run"
fi

echo ""

# 9. System Resources
print_header "9. System Resources"
echo "Container resource usage:"
docker stats --no-stream $CONTAINER
echo ""
echo "Disk usage:"
docker exec $CONTAINER df -h /mt4
echo ""

# 10. Recommendations
print_header "10. Diagnostic Summary"
ISSUES=0

if ! docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    print_error "MT4 is not running"
    ((ISSUES++))
fi

if ! docker exec $CONTAINER test -f /mt4/terminal.exe; then
    print_error "terminal.exe is missing"
    ((ISSUES++))
fi

if ! docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4; then
    print_warning "EA is not compiled"
    ((ISSUES++))
fi

if ! docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log; then
    print_warning "EA is not active"
    ((ISSUES++))
fi

# Check connection status
if [ -f ".env" ]; then
    source .env
    if [ "$MT4_LOGIN" = "your_demo_account" ] || [ -z "$MT4_LOGIN" ]; then
        print_error "MT4 login credentials not configured"
        ((ISSUES++))
    fi
fi

echo ""
if [ $ISSUES -eq 0 ]; then
    print_success "Everything is working correctly!"
else
    print_warning "Found $ISSUES issues"
    echo ""
    echo "Recommendations:"
    
    if ! docker exec $CONTAINER test -f /mt4/terminal.exe; then
        echo "1. Copy terminal.exe to the container:"
        echo "   docker cp terminal.exe ${CONTAINER}:/mt4/"
    fi
    
    if [ "$MT4_LOGIN" = "your_demo_account" ] || [ -z "$MT4_LOGIN" ]; then
        echo ""
        echo "2. Configure MT4 login credentials in .env file:"
        echo "   Example demo servers you can use:"
        echo "   - MetaQuotes-Demo (built-in demo)"
        echo "   - ICMarkets-Demo02"
        echo "   - Pepperstone-Demo01"
        echo "   - XM.COM-Demo 3"
        echo ""
        echo "   Edit .env file:"
        echo "   MT4_LOGIN=your_demo_account_number"
        echo "   MT4_PASSWORD=your_demo_password"
        echo "   MT4_SERVER=demo_server_name"
    fi
    
    if ! docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4; then
        echo ""
        echo "3. EA compilation requires active MT4 connection"
        echo "   - Ensure valid login credentials"
        echo "   - Check firewall/network settings"
        echo "   - Try manual compilation:"
        echo "     docker exec $CONTAINER wine /mt4/terminal.exe /compile:MQL4/Experts/AutoDeploy_EA.mq4"
    fi
    
    echo ""
    echo "4. Quick fixes to try:"
    echo "   a) Restart container: docker-compose restart"
    echo "   b) View logs: ./view_logs.sh"
    echo "   c) Connect via VNC: vncviewer localhost:5900"
    echo "   d) Check network: docker exec $CONTAINER ping -c 1 google.com"
fi

echo ""

# Quick connection test suggestion
print_header "11. Quick Connection Test"
echo "To quickly test with a demo account:"
echo ""
echo "1. Get a demo account from any broker (e.g., ICMarkets, XM, Pepperstone)"
echo "2. Update .env file with credentials:"
echo "   MT4_LOGIN=<demo_account_number>"
echo "   MT4_PASSWORD=<demo_password>"
echo "   MT4_SERVER=<demo_server>"
echo ""
echo "3. Restart container:"
echo "   docker-compose down"
echo "   docker-compose up -d"
echo ""
echo "4. Run this diagnostic again"

echo ""
echo "Diagnostic complete!"
