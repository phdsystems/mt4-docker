# Security & Deployment Guide

## Overview

This guide covers security hardening, monitoring setup, and deployment best practices for the MT4 Docker project.

## 🔒 Security Hardening

### 1. Docker Security

#### Container Security
- **Non-root user**: Containers run as `mt4user` (UID 1000)
- **Read-only root filesystem**: Prevents runtime modifications
- **Dropped capabilities**: Only essential capabilities retained
- **Security options**: `no-new-privileges:true` enabled

#### Secrets Management
```bash
# Create secrets directory
mkdir -p secrets
chmod 700 secrets

# Create secret files
echo "your_mt4_login" > secrets/mt4_login.txt
echo "your_mt4_password" > secrets/mt4_password.txt
echo "secure_vnc_password" > secrets/vnc_password.txt
echo "grafana_admin_password" > secrets/grafana_password.txt

# Set restrictive permissions
chmod 600 secrets/*.txt
```

#### Secure Deployment
```bash
# Use secure Docker Compose configuration
docker-compose -f docker-compose.secure.yml up -d
```

### 2. Network Security

#### Restricted Port Binding
- VNC: Only on localhost (127.0.0.1:5900)
- Prometheus: Only on localhost (127.0.0.1:9090)
- Grafana: Only on localhost (127.0.0.1:3000)

#### Access via SSH Tunnel
```bash
# Create SSH tunnel for VNC access
ssh -L 5900:localhost:5900 user@server

# Create SSH tunnel for monitoring
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 user@server
```

### 3. File Permissions

```bash
# Set proper ownership
chown -R 1000:1000 MQL4/
chown -R 1000:1000 logs/

# Restrict permissions
find MQL4/ -type f -exec chmod 644 {} \;
find MQL4/ -type d -exec chmod 755 {} \;
chmod 600 secrets/*
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration

#### Start Monitoring Stack
```bash
# Create monitoring directories
mkdir -p monitoring/prometheus/alerts
mkdir -p monitoring/grafana/provisioning/dashboards

# Deploy monitoring stack
docker-compose -f docker-compose.secure.yml up -d prometheus grafana node-exporter
```

#### Access Dashboards
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/[secret])

### 2. Alerts Configuration

Alerts are configured for:
- MT4 terminal down
- High CPU/memory usage
- Connection lost
- High message queue lag
- Low disk space

### 3. Custom Metrics

The MT4 exporter provides:
- Account balance/equity
- Connection status
- Open positions/orders
- Tick rates by symbol
- Resource usage

## 🚀 Automated Deployment

### 1. CI/CD Pipeline

#### GitHub Actions Workflow
- **Code Quality**: Linting, formatting, security scanning
- **Testing**: Unit tests with coverage, integration tests
- **Security**: Container scanning, dependency checks
- **Performance**: Automated benchmarks
- **Deployment**: Automated Docker image builds

#### Enable CI/CD
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run all checks locally
pre-commit run --all-files
```

### 2. Performance Benchmarks

#### Run Benchmarks
```bash
# Install dependencies
pip install -r requirements.txt

# Run ZeroMQ benchmarks
python tests/performance/benchmark_zmq.py

# Run pytest benchmarks
pytest tests/performance/ --benchmark-only
```

#### Expected Performance
- Throughput: 50,000+ messages/second
- Latency: < 1ms average
- Scalability: 50+ concurrent subscribers

### 3. Health Checks

#### Container Health
```bash
# Check container health
docker-compose ps
docker-compose exec mt4 /healthcheck.sh

# View logs
docker-compose logs -f mt4
```

#### Application Health
- MT4 terminal process monitoring
- ZeroMQ bridge connectivity
- Resource usage tracking

## 🛡️ Security Best Practices

### 1. Regular Updates

```bash
# Update base images
docker-compose pull
docker-compose build --no-cache

# Update dependencies
pip install --upgrade -r requirements.txt
```

### 2. Security Scanning

```bash
# Scan Docker images
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image mt4-docker:latest

# Scan Python dependencies
pip install safety
safety check -r requirements.txt

# Scan for secrets
pip install detect-secrets
detect-secrets scan --all-files
```

### 3. Backup & Recovery

```bash
# Backup configuration
tar -czf mt4-backup-$(date +%Y%m%d).tar.gz \
  MQL4/Experts/*.mq4 \
  config/ \
  secrets/

# Backup volumes
docker run --rm -v mt4_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mt4-data-$(date +%Y%m%d).tar.gz /data
```

## 📈 Production Deployment

### 1. Environment Setup

```bash
# Production environment variables
export MT4_SERVER="your.broker.server:443"
export ENVIRONMENT="production"
export LOG_LEVEL="WARNING"
```

### 2. Resource Allocation

```yaml
# docker-compose.prod.yml
services:
  mt4:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

### 3. Monitoring & Alerting

```bash
# Configure Alertmanager
cat > monitoring/alertmanager/config.yml << EOF
global:
  slack_api_url: 'YOUR_SLACK_WEBHOOK'

route:
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - channel: '#mt4-alerts'
        title: 'MT4 Alert'
EOF
```

## 🔧 Troubleshooting

### Common Issues

1. **Connection Issues**
   ```bash
   # Check connectivity
   docker-compose exec mt4 netstat -an | grep 5556
   docker-compose exec zeromq-bridge python -c "import zmq; print(zmq.zmq_version())"
   ```

2. **Performance Issues**
   ```bash
   # Check resource usage
   docker stats mt4-docker
   docker-compose exec mt4 top
   ```

3. **Security Violations**
   ```bash
   # Check security context
   docker-compose exec mt4 id
   docker-compose exec mt4 ls -la /mt4
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up

# Enable Wine debug output
docker-compose exec mt4 bash -c "WINEDEBUG=+all wine terminal.exe"
```

## 📋 Checklist

### Pre-deployment
- [ ] Secrets configured
- [ ] Firewall rules set
- [ ] SSL certificates ready
- [ ] Backup strategy defined
- [ ] Monitoring configured

### Post-deployment
- [ ] Health checks passing
- [ ] Metrics flowing
- [ ] Alerts configured
- [ ] Performance validated
- [ ] Security scans clean

### Maintenance
- [ ] Weekly security updates
- [ ] Monthly performance review
- [ ] Quarterly security audit
- [ ] Annual architecture review

## 🚨 Emergency Procedures

### Service Recovery
```bash
# Quick restart
docker-compose restart mt4

# Full recovery
docker-compose down
docker-compose up -d

# Data recovery
docker-compose down
docker volume rm mt4_data
# Restore from backup
docker-compose up -d
```

### Security Incident
1. Isolate affected containers
2. Collect logs for analysis
3. Rotate all credentials
4. Apply security patches
5. Document incident

## 📚 Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [ZeroMQ Security](http://api.zeromq.org/master:zmq-curve)