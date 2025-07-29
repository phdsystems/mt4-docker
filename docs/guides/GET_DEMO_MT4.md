# How to Get a Demo MT4 Terminal

## Popular Brokers Offering MT4 Demo

### 1. IG Markets
- **URL**: https://www.ig.com/en/trading-platforms/mt4
- **Server Names**: IG-DEMO, IG-LIVE (for demo accounts)
- **Steps**:
  1. Register for demo account at IG.com
  2. Download MT4 from client portal
  3. Login credentials sent via email
  4. Extract terminal.exe from installation
- **Note**: One of the largest CFD brokers globally

### 2. IC Markets
- **URL**: https://www.icmarkets.com/global/en/trading-platforms/metatrader-4/
- **Server Names**: ICMarketsSC-Demo01, ICMarketsSC-Demo02
- **Steps**:
  1. Register for demo account
  2. Download MT4 for Windows
  3. Extract terminal.exe from installation

### 2. XM Trading
- **URL**: https://www.xm.com/mt4
- **Server Names**: XMGlobal-Demo 3
- **Steps**:
  1. Create demo account
  2. Download MT4 installer
  3. Install and copy terminal.exe

### 3. FXCM
- **URL**: https://www.fxcm.com/markets/platforms/metatrader-4/
- **Server Names**: FXCM-Demo01
- **Note**: Provides direct MT4 download after demo registration

### 4. Pepperstone
- **URL**: https://pepperstone.com/en/trading/platforms/metatrader-4/
- **Server Names**: Pepperstone-Demo01
- **Features**: Fast execution, multiple asset classes

### 5. FBS
- **URL**: https://fbs.com/en/trading/platforms/metatrader-4
- **Server Names**: FBS-Demo
- **Note**: Simple registration process

## Extracting terminal.exe

Once you download and install MT4:

### Windows:
```bash
# Default installation path
C:\Program Files (x86)\MetaTrader 4\terminal.exe

# Or for specific broker
C:\Program Files (x86)\IC Markets MetaTrader 4\terminal.exe
```

### Using Wine (Linux/Mac):
```bash
# Download MT4 installer
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe

# Install with Wine
wine mt4setup.exe

# Find terminal.exe
find ~/.wine -name "terminal.exe" -type f
```

## Quick Demo Setup Script

Create a script to automate demo setup:

```bash
#!/bin/bash
# File: setup_demo.sh

echo "Setting up MT4 Demo..."

# Create demo .env file
cat > .env << EOF
# Demo Account Configuration
MT4_LOGIN=123456
MT4_PASSWORD=DemoPassword123
MT4_SERVER=ICMarketsSC-Demo01
VNC_PASSWORD=demo_vnc_pass
EOF

echo "Demo .env created!"
echo "Note: You'll need to:"
echo "1. Download MT4 from a broker"
echo "2. Copy terminal.exe here"
echo "3. Update .env with your demo credentials"
```

## Testing with Generic MT4

For testing purposes only, you can use the generic MetaTrader 4 from MetaQuotes:

1. Visit: https://www.metatrader4.com/en/download
2. Download the installer
3. Install and locate terminal.exe
4. Use any broker's demo server from the list above

## Common Demo Servers

Here are commonly available demo servers you can try:

```
IG-DEMO
IG-LIVE
ICMarketsSC-Demo01
ICMarketsSC-Demo02
XMGlobal-Demo 3
Pepperstone-Demo01
FBS-Demo
FXCM-Demo01
Alpari-Demo
FxPro-Demo
```

## Important Notes

1. **Demo accounts** usually expire after 30-90 days
2. **Server names** may change - check broker's email after registration
3. **terminal.exe** is the same for all brokers - only server connection differs
4. **File size**: terminal.exe is typically 1-2 MB

## Testing Your Setup with VNC

Once you have MT4 running in Docker, you can connect via VNC to see it visually:

### VNC Clients
- **Windows**: TightVNC, RealVNC Viewer, UltraVNC
- **macOS**: Built-in Screen Sharing (Finder → Go → Connect to Server → vnc://localhost:5900)
- **Linux**: Remmina (usually pre-installed), TigerVNC

### Connection
```bash
Server: localhost:5900
Password: (from your .env file)
```

This allows you to:
- Verify MT4 is running correctly
- Log in with your demo credentials
- See charts and EA activity
- Debug any connection issues

## Automated Demo Download (Linux)

```bash
#!/bin/bash
# download_mt4_demo.sh

# Create directory for download
mkdir -p mt4_download
cd mt4_download

# Download generic MT4 (example)
echo "Downloading MT4 installer..."
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe

# Extract with 7zip (if available)
if command -v 7z &> /dev/null; then
    7z x mt4setup.exe
    find . -name "terminal.exe" -exec cp {} ../terminal.exe \;
    echo "terminal.exe extracted!"
else
    echo "Please install p7zip-full to auto-extract"
    echo "Or run installer with Wine and copy terminal.exe manually"
fi

cd ..
rm -rf mt4_download
```

Save this guide and use any of these brokers to get a working demo terminal.exe for testing!