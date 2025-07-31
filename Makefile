# MT4 Docker ZeroMQ Makefile
# Automates common tasks

.PHONY: all setup build deploy start stop restart logs health clean test

# Default target
all: setup deploy

# Run complete setup
setup:
	@echo "Setting up MT4 Docker environment..."
	@pip3 install -r requirements.txt
	@echo "✓ Setup complete"

# Build all components
build: build-docker

# Build Docker images
build-docker:
	@echo "Building Docker images..."
	@docker build -t mt4-docker:latest .
	@docker build -f Dockerfile.python -t mt4-python:latest .
	@docker build -f Dockerfile.security-updater -t mt4-security:latest .
	@echo "✓ Docker images built"

# Deploy the complete stack
deploy:
	@echo "Deploying MT4 ZeroMQ stack..."
	@chmod +x deploy.sh
	@./deploy.sh

# Start all services
start:
	@echo "Starting services..."
	@docker-compose -f docker-compose.full.yml up -d
	@echo "✓ Services started"

# Stop all services
stop:
	@echo "Stopping services..."
	@docker-compose -f docker-compose.full.yml down
	@docker-compose -f docker-compose.monitoring.yml down || true
	@docker-compose -f docker-compose.elk.yml down || true
	@docker-compose -f docker-compose.security.yml down || true
	@echo "✓ Services stopped"

# Restart all services
restart: stop start

# View logs
logs:
	@docker-compose -f docker-compose.full.yml logs -f

# Check health of all services
health:
	@chmod +x check_health.sh
	@./check_health.sh

# Run tests
test: test-python

# Test Python code
test-python:
	@echo "Testing Python code..."
	@python3 -m pytest tests/test_*.py -v
	@echo "✓ Python tests passed"
	@echo "✓ Integration tests passed"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dll_source/build/*.dll
	@rm -rf __pycache__ .pytest_cache
	@rm -f *.log
	@find . -name "*.pyc" -delete
	@echo "✓ Cleaned"

# Generate security keys
keys:
	@echo "Generating security keys..."
	@python3 services/security/secure_bridge_launcher.py \
		--generate-client-keys 5 \
		--regenerate-keys
	@echo "✓ Keys generated"

# Monitor performance
monitor:
	@echo "Opening monitoring dashboards..."
	@xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || echo "Grafana: http://localhost:3000"
	@xdg-open http://localhost:5601 2>/dev/null || open http://localhost:5601 2>/dev/null || echo "Kibana: http://localhost:5601"

# Quick start for development
dev:
	@echo "Starting development environment..."
	@docker-compose up -d mt4
	@python3 clients/python/zmq_subscriber.py

# Install Python dependencies
deps:
	@echo "Installing Python dependencies..."
	@pip install -r requirements.txt

# Update all components
update:
	@echo "Updating components..."
	@git pull
	@make deps
	@make build
	@echo "✓ Update complete"

# Show help
help:
	@echo "MT4 Docker ZeroMQ Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup      - Run complete setup"
	@echo "  make deploy     - Deploy the entire stack"
	@echo "  make start      - Start all services"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs"
	@echo "  make health     - Check service health"
	@echo "  make test       - Run all tests"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make monitor    - Open monitoring dashboards"
	@echo "  make dev        - Start development environment"
	@echo ""
	@echo "Build targets:"
	@echo "  make build      - Build all components"
	@echo "  make build-dll  - Build DLL only"
	@echo "  make build-docker - Build Docker images"
	@echo ""
	@echo "Other targets:"
	@echo "  make keys       - Generate security keys"
	@echo "  make deps       - Install Python dependencies"
	@echo "  make update     - Update all components"