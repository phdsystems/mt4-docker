#!/bin/bash
#
# Automated MT4-ZeroMQ Integration Setup Script
# Sets up the entire MT4 Docker environment with ZeroMQ streaming
#

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/setup.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check MinGW for DLL compilation
    if ! command -v i686-w64-mingw32-g++ &> /dev/null; then
        warn "MinGW not found. Installing..."
        sudo apt-get update
        sudo apt-get install -y mingw-w64
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed. Please install Python 3."
    fi
    
    log "✓ All requirements satisfied"
}

build_dll() {
    log "Building MT4ZMQ DLL..."
    
    cd "$PROJECT_ROOT/dll_source"
    
    # Create build directory
    mkdir -p build
    
    # Compile DLL
    i686-w64-mingw32-g++ -shared -o build/mt4zmq.dll \
        mt4zmq_winsock_fixed.cpp \
        -lws2_32 -static-libgcc -static-libstdc++ \
        -Wl,--kill-at -Wl,--enable-stdcall-fixup \
        -DUNICODE -D_UNICODE
    
    if [ -f "build/mt4zmq.dll" ]; then
        log "✓ DLL built successfully"
        
        # Copy to MT4 Libraries
        cp build/mt4zmq.dll "$PROJECT_ROOT/MQL4/Libraries/"
        log "✓ DLL copied to MQL4/Libraries/"
    else
        error "Failed to build DLL"
    fi
    
    cd "$PROJECT_ROOT"
}

setup_python_environment() {
    log "Setting up Python environment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    
    # Create requirements.txt if not exists
    if [ ! -f "requirements.txt" ]; then
        cat > requirements.txt << EOF
pyzmq==25.1.1
pandas==2.0.3
numpy==1.24.3
requests==2.31.0
prometheus-client==0.18.0
flask==3.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
pip-audit==2.6.1
safety==2.3.5
EOF
    fi
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log "✓ Python environment ready"
}

build_docker_images() {
    log "Building Docker images..."
    
    # Build MT4 Docker image
    docker build -t mt4-docker:latest .
    
    # Build security updater
    if [ -f "Dockerfile.security-updater" ]; then
        docker build -f Dockerfile.security-updater -t mt4-security-updater:latest .
    fi
    
    log "✓ Docker images built"
}

generate_security_keys() {
    log "Generating security keys..."
    
    # Run key generation
    if [ -f "services/security/secure_bridge_launcher.py" ]; then
        python3 services/security/secure_bridge_launcher.py \
            --generate-client-keys 3 \
            --regenerate-keys \
            --keys-dir ./keys
    fi
    
    log "✓ Security keys generated"
}

create_config_files() {
    log "Creating configuration files..."
    
    # Create .env file if not exists
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# MT4 Configuration
MT4_SERVER=demo.server.com:443
MT4_LOGIN=12345
MT4_PASSWORD=password

# ZeroMQ Configuration
ZMQ_PUB_ADDRESS=tcp://*:5556
ZMQ_SUB_ADDRESS=tcp://localhost:5556

# Security
ENABLE_SSL=true
SLACK_WEBHOOK_URL=
SECURITY_EMAIL=admin@example.com

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# ELK Stack
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601
LOGSTASH_PORT=5000
EOF
        log "✓ Created .env file"
    fi
    
    # Create docker-compose.override.yml for local development
    if [ ! -f "docker-compose.override.yml" ]; then
        cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  mt4:
    volumes:
      - ./MQL4:/mt4/MQL4
      - ./logs:/mt4/logs
    environment:
      - DEBUG=true
EOF
        log "✓ Created docker-compose.override.yml"
    fi
}

create_automation_scripts() {
    log "Creating automation scripts..."
    
    # Create start script
    cat > start_all.sh << 'EOF'
#!/bin/bash
# Start all services

echo "Starting MT4 Docker Stack..."

# Start MT4 and ZeroMQ bridge
docker-compose up -d

# Wait for MT4 to start
echo "Waiting for MT4 to initialize..."
sleep 30

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Start ELK stack
docker-compose -f docker-compose.elk.yml up -d

# Start security monitoring
docker-compose -f docker-compose.security.yml up -d

echo "All services started!"
echo ""
echo "Available services:"
echo "  - MT4 Terminal: VNC on port 5900"
echo "  - ZeroMQ Publisher: tcp://localhost:5556"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000"
echo "  - Kibana: http://localhost:5601"
echo ""
echo "To view logs: docker-compose logs -f"
EOF
    chmod +x start_all.sh
    
    # Create stop script
    cat > stop_all.sh << 'EOF'
#!/bin/bash
# Stop all services

echo "Stopping all services..."

docker-compose down
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.elk.yml down
docker-compose -f docker-compose.security.yml down

echo "All services stopped"
EOF
    chmod +x stop_all.sh
    
    # Create health check script
    cat > check_health.sh << 'EOF'
#!/bin/bash
# Check health of all services

echo "Checking service health..."

# Check Docker containers
echo -e "\n=== Docker Containers ==="
docker-compose ps

# Check ZeroMQ
echo -e "\n=== ZeroMQ Status ==="
nc -zv localhost 5556 && echo "✓ ZeroMQ is listening" || echo "✗ ZeroMQ is not responding"

# Check Prometheus
echo -e "\n=== Prometheus Status ==="
curl -s http://localhost:9090/-/healthy && echo "✓ Prometheus is healthy" || echo "✗ Prometheus is not responding"

# Check Elasticsearch
echo -e "\n=== Elasticsearch Status ==="
curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green\|yellow"' && echo "✓ Elasticsearch is healthy" || echo "✗ Elasticsearch is not responding"

# Check Python subscriber
echo -e "\n=== Testing ZeroMQ Subscriber ==="
timeout 5 python3 -c "
import zmq
ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect('tcp://localhost:5556')
sub.subscribe(b'')
sub.setsockopt(zmq.RCVTIMEO, 1000)
try:
    topic, msg = sub.recv_multipart()
    print('✓ Receiving messages:', topic.decode()[:20] + '...')
except:
    print('✗ No messages received (EA might not be running)')
"
EOF
    chmod +x check_health.sh
    
    log "✓ Automation scripts created"
}

setup_mt4_ea() {
    log "Setting up MT4 Expert Advisor..."
    
    # Create EA auto-installer script
    cat > "$PROJECT_ROOT/MQL4/Scripts/AutoInstallZMQ.mq4" << 'EOF'
//+------------------------------------------------------------------+
//|                                              AutoInstallZMQ.mq4  |
//|                       Automatically install and configure ZMQ EA |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property version   "1.00"
#property strict

void OnStart()
{
    // Copy EA to correct location
    string source = "MT4ZMQBridge.mq4";
    string target = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Experts\\MT4ZMQBridge.mq4";
    
    Print("Installing MT4ZMQ Bridge EA...");
    
    // Check if EA exists
    if (FileIsExist(source, FILE_COMMON))
    {
        // Copy file
        if (FileCopy(source, 0, target, FILE_REWRITE))
        {
            Print("✓ EA installed successfully");
            Print("Please compile the EA in MetaEditor");
        }
        else
        {
            Print("✗ Failed to install EA");
        }
    }
    else
    {
        Print("✗ Source EA not found");
    }
    
    // Display instructions
    Comment("MT4 ZeroMQ Setup Instructions:\n\n" +
            "1. Open MetaEditor (F4)\n" +
            "2. Compile MT4ZMQBridge.mq4\n" +
            "3. Go to Tools → Options → Expert Advisors\n" +
            "4. Enable 'Allow DLL imports'\n" +
            "5. Drag MT4ZMQBridge to a chart\n" +
            "6. Click OK to start streaming");
}
EOF
    
    log "✓ MT4 EA setup complete"
}

create_docker_compose_full() {
    log "Creating complete Docker Compose configuration..."
    
    cat > docker-compose.full.yml << 'EOF'
version: '3.8'

services:
  # MT4 with ZeroMQ
  mt4:
    build: .
    container_name: mt4_terminal
    ports:
      - "5900:5900"  # VNC
    volumes:
      - ./MQL4:/mt4/MQL4
      - ./logs/mt4:/mt4/logs
      - mt4_data:/mt4/Data
    environment:
      - DISPLAY=:1
      - MT4_SERVER=${MT4_SERVER}
      - MT4_LOGIN=${MT4_LOGIN}
      - MT4_PASSWORD=${MT4_PASSWORD}
    networks:
      - mt4_network
    healthcheck:
      test: ["CMD", "pgrep", "terminal.exe"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Python ZeroMQ Subscriber
  zmq-subscriber:
    build:
      context: .
      dockerfile: Dockerfile.python
    container_name: mt4_zmq_subscriber
    command: python3 clients/python/secure_market_client.py
    volumes:
      - ./clients:/app/clients
      - ./services:/app/services
      - ./keys:/app/keys
      - ./logs/subscriber:/app/logs
    environment:
      - ZMQ_SUB_ADDRESS=tcp://mt4:5556
      - LOG_LEVEL=INFO
    networks:
      - mt4_network
    depends_on:
      - mt4

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: mt4_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - mt4_network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: mt4_grafana
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - mt4_network

  # Elasticsearch
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: mt4_elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - mt4_network

  # Kibana
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: mt4_kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - mt4_network
    depends_on:
      - elasticsearch

  # Security Updater
  security-updater:
    build:
      context: .
      dockerfile: Dockerfile.security-updater
    container_name: mt4_security_updater
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - security_logs:/app/logs
      - ./config/security:/app/config:ro
    environment:
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
      - SECURITY_EMAIL=${SECURITY_EMAIL}
    networks:
      - mt4_network

volumes:
  mt4_data:
  prometheus_data:
  grafana_data:
  elasticsearch_data:
  security_logs:

networks:
  mt4_network:
    driver: bridge
EOF
    
    log "✓ Complete Docker Compose configuration created"
}

create_one_click_deploy() {
    log "Creating one-click deployment script..."
    
    cat > deploy.sh << 'EOF'
#!/bin/bash
#
# One-Click MT4 ZeroMQ Deployment
#

set -e

echo "=========================================="
echo "   MT4 ZeroMQ One-Click Deployment"
echo "=========================================="

# Check if setup has been run
if [ ! -f "setup.log" ]; then
    echo "Running initial setup..."
    ./scripts/setup_mt4_zmq.sh
fi

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start all services
echo -e "\n Starting services..."
docker-compose -f docker-compose.full.yml up -d

# Wait for services
echo -e "\n Waiting for services to initialize..."
sleep 30

# Check health
echo -e "\n Checking service health..."
./check_health.sh

# Display access information
echo -e "\n=========================================="
echo "   Deployment Complete!"
echo "=========================================="
echo ""
echo "Access Points:"
echo "  VNC (MT4):        vnc://localhost:5900"
echo "  ZeroMQ:           tcp://localhost:5556"
echo "  Prometheus:       http://localhost:9090"
echo "  Grafana:          http://localhost:3000 (admin/admin)"
echo "  Kibana:           http://localhost:5601"
echo ""
echo "Quick Commands:"
echo "  View logs:        docker-compose -f docker-compose.full.yml logs -f"
echo "  Stop all:         docker-compose -f docker-compose.full.yml down"
echo "  Health check:     ./check_health.sh"
echo ""
echo "Next Steps:"
echo "  1. Connect to MT4 via VNC"
echo "  2. Enable DLL imports in MT4 settings"
echo "  3. Attach MT4ZMQBridge EA to a chart"
echo "  4. Monitor data in Grafana/Kibana"
echo ""
EOF
    chmod +x deploy.sh
    
    log "✓ One-click deployment script created"
}

# Main execution
main() {
    echo "=========================================="
    echo "   MT4-ZeroMQ Automated Setup"
    echo "=========================================="
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Initialize log
    echo "Setup started at $(date)" > "$LOG_FILE"
    
    # Run setup steps
    check_requirements
    build_dll
    setup_python_environment
    build_docker_images
    generate_security_keys
    create_config_files
    create_automation_scripts
    setup_mt4_ea
    create_docker_compose_full
    create_one_click_deploy
    
    # Summary
    echo ""
    echo "=========================================="
    echo "   Setup Complete!"
    echo "=========================================="
    echo ""
    echo "To deploy the entire stack, run:"
    echo "  ./deploy.sh"
    echo ""
    echo "For manual control:"
    echo "  Start all:  ./start_all.sh"
    echo "  Stop all:   ./stop_all.sh"
    echo "  Check:      ./check_health.sh"
    echo ""
    
    log "Setup completed successfully!"
}

# Run main function
main "$@"
EOF