# MT4 Docker ZeroMQ - Automated Setup Guide

## 🚀 Quick Start (One Command!)

```bash
make deploy
```

This single command will:
1. Check system requirements
2. Build the ZeroMQ DLL
3. Set up Python environment
4. Build Docker images
5. Generate security keys
6. Create configurations
7. Deploy the entire stack
8. Start all services

## 📋 Prerequisites

- Ubuntu/Debian Linux (or WSL2 on Windows)
- Docker and Docker Compose installed
- Internet connection for downloading dependencies

## 🎯 Automated Setup Options

### Option 1: Using Make (Recommended)

```bash
# Complete setup and deployment
make deploy

# Or step by step:
make setup      # Initial setup
make build      # Build components
make start      # Start services
make health     # Check health
```

### Option 2: Using Setup Script

```bash
# Run automated setup
./scripts/setup_mt4_zmq.sh

# Then deploy
./deploy.sh
```

### Option 3: Manual Steps

```bash
# 1. Build DLL
cd dll_source
./build.sh

# 2. Setup Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Generate keys
python3 services/security/secure_bridge_launcher.py --generate-client-keys 3

# 4. Start services
docker-compose -f docker-compose.full.yml up -d
```

## 🔧 Configuration

### Environment Variables (.env)

The setup creates a `.env` file with:

```env
# MT4 Configuration
MT4_SERVER=demo.server.com:443
MT4_LOGIN=12345
MT4_PASSWORD=password

# ZeroMQ Configuration
ZMQ_PUB_ADDRESS=tcp://*:5556
ZMQ_SUB_ADDRESS=tcp://localhost:5556

# Security
ENABLE_SSL=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SECURITY_EMAIL=admin@example.com
```

Edit this file before deployment to use your MT4 credentials.

## 📊 What Gets Deployed

The automated setup deploys:

1. **MT4 Terminal** - Running in Docker with VNC access
2. **ZeroMQ Bridge** - DLL-based high-performance streaming
3. **Python Subscribers** - Secure clients for data consumption
4. **Prometheus** - Metrics collection
5. **Grafana** - Real-time dashboards
6. **ELK Stack** - Centralized logging
7. **Security Monitor** - Automated vulnerability scanning

## 🖥️ Accessing Services

After deployment, services are available at:

| Service | URL/Port | Credentials |
|---------|----------|-------------|
| MT4 VNC | vnc://localhost:5900 | No password |
| ZeroMQ Publisher | tcp://localhost:5556 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |
| Kibana | http://localhost:5601 | - |
| Elasticsearch | http://localhost:9200 | - |

## 🔍 Common Commands

```bash
# View logs
make logs

# Check health
make health

# Stop everything
make stop

# Restart services
make restart

# Run tests
make test

# Open monitoring
make monitor

# Development mode
make dev
```

## 📝 MT4 Setup Steps

After deployment, in MT4:

1. Connect via VNC: `vnc://localhost:5900`
2. Go to Tools → Options → Expert Advisors
3. Check "Allow DLL imports"
4. Open Navigator (Ctrl+N)
5. Drag `MT4ZMQBridge` EA to a chart
6. Configure parameters and click OK

## 🧪 Testing the Setup

### Quick Test

```bash
# Test ZeroMQ connection
python3 -c "
import zmq
ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect('tcp://localhost:5556')
sub.subscribe(b'')
sub.setsockopt(zmq.RCVTIMEO, 5000)
try:
    topic, msg = sub.recv_multipart()
    print(f'✓ Receiving: {topic.decode()} - {msg.decode()[:50]}...')
except:
    print('✗ No messages (check if EA is running in MT4)')
"
```

### Full Test Suite

```bash
# Run all tests
make test

# Or individually:
make test-dll      # Test DLL
make test-python   # Test Python code
make test-integration  # Integration tests
```

## 🔧 Troubleshooting

### Issue: Services won't start

```bash
# Check Docker
docker version
docker-compose version

# Check ports
netstat -tlnp | grep -E "(5556|5900|9090|3000)"

# Reset and retry
make clean
make stop
make deploy
```

### Issue: No data from MT4

1. Check MT4 EA is running (smiley face on chart)
2. Verify DLL imports are enabled
3. Check logs: `docker logs mt4_terminal`
4. Test DLL: Run `TestZMQDLLIntegration` script in MT4

### Issue: Can't connect to VNC

```bash
# Check VNC is running
docker exec mt4_terminal ps aux | grep vnc

# Restart MT4 container
docker-compose restart mt4

# Try alternate VNC viewer
sudo apt-get install tigervnc-viewer
vncviewer localhost:5900
```

## 🔄 Updating

```bash
# Pull latest changes
git pull

# Update and rebuild
make update

# Or manually:
make stop
make clean
make build
make start
```

## 🛡️ Security

The automated setup includes:

- CURVE authentication for ZeroMQ
- SSL/TLS encryption options
- Automated security scanning
- Key rotation capabilities
- Audit logging

To regenerate security keys:

```bash
make keys
```

## 📊 Performance Tuning

Edit `docker-compose.full.yml` to adjust:

```yaml
services:
  mt4:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

## 🎯 Next Steps

1. **Customize EA Parameters**
   - Edit EA settings in MT4
   - Adjust symbols to stream
   - Set update intervals

2. **Create Custom Dashboards**
   - Import Grafana dashboards
   - Configure Kibana visualizations
   - Set up alerts

3. **Integrate Your Systems**
   - Use Python client examples
   - Subscribe to specific topics
   - Process market data

## 📚 Documentation

- [MT4 DLL Integration](docs/MT4_DLL_INTEGRATION.md)
- [SSL/TLS Implementation](docs/SSL_TLS_IMPLEMENTATION.md)
- [ELK Stack Guide](docs/ELK_STACK_GUIDE.md)
- [Security Updates Guide](docs/SECURITY_UPDATES_GUIDE.md)

## 💡 Tips

- Use `make dev` for development mode
- Monitor logs with `make logs`
- Set up cron for `make health` checks
- Use `make monitor` to open dashboards
- Run `make test` before production

The entire MT4-ZeroMQ integration is now fully automated!