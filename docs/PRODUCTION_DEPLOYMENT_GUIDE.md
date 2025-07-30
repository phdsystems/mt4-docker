# Production Deployment Guide for MT4 Docker ZeroMQ

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Hardware Requirements](#hardware-requirements)
3. [Network Configuration](#network-configuration)
4. [Pre-Deployment Checklist](#pre-deployment-checklist)
5. [Deployment Steps](#deployment-steps)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Performance Tuning](#performance-tuning)
8. [High Availability Setup](#high-availability-setup)
9. [Monitoring and Alerting](#monitoring-and-alerting)
10. [Maintenance Procedures](#maintenance-procedures)

## Prerequisites

### System Requirements
- Ubuntu 20.04 LTS or newer (recommended) / CentOS 8+ / RHEL 8+
- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.8+
- 10GB+ free disk space

### Required Expertise
- Linux system administration
- Docker container management
- Network security basics
- MT4 platform knowledge

## Hardware Requirements

### Minimum Production Specifications

| Component | Minimum | Recommended | High-Performance |
|-----------|---------|-------------|------------------|
| CPU | 4 cores | 8 cores | 16+ cores |
| RAM | 8 GB | 16 GB | 32+ GB |
| Storage | 100 GB SSD | 250 GB SSD | 500+ GB NVMe |
| Network | 100 Mbps | 1 Gbps | 10 Gbps |

### Scaling Considerations

```yaml
# Resource allocation per component
mt4_terminal: 2 CPU, 4GB RAM
zeromq_bridge: 1 CPU, 2GB RAM
elasticsearch: 2 CPU, 4GB RAM
prometheus: 1 CPU, 2GB RAM
grafana: 0.5 CPU, 1GB RAM
```

## Network Configuration

### 1. Firewall Rules

```bash
# Required ports
sudo ufw allow 22/tcp    # SSH (restrict source IPs)
sudo ufw allow 5900/tcp  # VNC (internal only)
sudo ufw allow 5556/tcp  # ZeroMQ Publisher
sudo ufw allow 3000/tcp  # Grafana
sudo ufw allow 9090/tcp  # Prometheus
sudo ufw allow 5601/tcp  # Kibana

# Production: Restrict to specific IPs
sudo ufw allow from 10.0.0.0/24 to any port 5556
sudo ufw allow from 10.0.0.0/24 to any port 3000
```

### 2. SSL/TLS Configuration

```nginx
# /etc/nginx/sites-available/mt4-services
server {
    listen 443 ssl http2;
    server_name mt4.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/mt4.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mt4.yourdomain.com/privkey.pem;
    
    # Grafana
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Kibana
    location /kibana {
        proxy_pass http://localhost:5601;
        proxy_set_header Host $host;
        rewrite ^/kibana(.*)$ $1 break;
    }
}
```

### 3. DNS Configuration

```bash
# Production DNS records
mt4.yourdomain.com         A     203.0.113.10
mt4-dr.yourdomain.com      A     203.0.113.20
prometheus.yourdomain.com  CNAME mt4.yourdomain.com
grafana.yourdomain.com     CNAME mt4.yourdomain.com
```

## Pre-Deployment Checklist

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate new ZeroMQ security keys
- [ ] Configure firewall rules
- [ ] Enable SELinux/AppArmor
- [ ] Set up fail2ban
- [ ] Configure SSL certificates
- [ ] Review security policies

### Configuration Checklist

- [ ] Update `.env` with production values
- [ ] Configure MT4 broker credentials
- [ ] Set monitoring thresholds
- [ ] Configure backup locations
- [ ] Set log retention policies
- [ ] Configure alerting channels

### Testing Checklist

- [ ] Run full test suite
- [ ] Perform load testing
- [ ] Test failover procedures
- [ ] Verify backup/restore
- [ ] Test monitoring alerts
- [ ] Validate security scanning

## Deployment Steps

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    docker.io \
    docker-compose \
    git \
    htop \
    iotop \
    nethogs \
    fail2ban \
    ufw

# Configure Docker
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# Configure swap (if needed)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/mt4-docker.git
cd mt4-docker

# Copy production config
cp .env.production .env

# Edit configuration
nano .env

# Generate security keys
make keys

# Build images
make build
```

### 3. Deploy Services

```bash
# Deploy in stages for verification

# Stage 1: Core services
docker-compose up -d mt4 zmq-subscriber

# Verify core services
docker-compose ps
docker-compose logs -f mt4

# Stage 2: Monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# Stage 3: Logging
docker-compose -f docker-compose.elk.yml up -d

# Stage 4: Security
docker-compose -f docker-compose.security.yml up -d
```

### 4. Verify Deployment

```bash
# Run health checks
./check_health.sh

# Test ZeroMQ streaming
python3 tests/test_performance.py

# Check monitoring
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

## Post-Deployment Configuration

### 1. Configure MT4 EA

```mql4
// Production EA settings
input string  InpPublishAddress = "tcp://*:5556";
input string  InpSymbols = "EURUSD,GBPUSD,USDJPY,AUDUSD,XAUUSD";
input int     InpTickInterval = 100;
input bool    InpPublishTicks = true;
input bool    InpPublishBars = true;
input bool    InpVerboseLogging = false;  // Disable in production
```

### 2. Set Up Monitoring Alerts

```yaml
# prometheus/alerts.yml
groups:
  - name: mt4_alerts
    rules:
      - alert: MT4Disconnected
        expr: up{job="mt4"} == 0
        for: 5m
        annotations:
          summary: "MT4 terminal is disconnected"
          
      - alert: HighMessageLatency
        expr: zmq_message_latency_ms > 10
        for: 5m
        annotations:
          summary: "High ZeroMQ message latency"
          
      - alert: LowThroughput
        expr: rate(zmq_messages_total[5m]) < 100
        for: 10m
        annotations:
          summary: "Low message throughput"
```

### 3. Configure Backups

```bash
# /etc/cron.d/mt4-backup
0 2 * * * root /opt/mt4-docker/scripts/backup.sh
0 */6 * * * root /opt/mt4-docker/scripts/backup_config.sh
```

## Performance Tuning

### 1. System Tuning

```bash
# /etc/sysctl.d/99-mt4.conf
# Network optimizations
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr

# File descriptor limits
fs.file-max = 2097152

# Apply settings
sudo sysctl -p /etc/sysctl.d/99-mt4.conf
```

### 2. Docker Tuning

```yaml
# docker-compose.production.yml
services:
  mt4:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

### 3. ZeroMQ Tuning

```python
# High-performance ZeroMQ settings
socket.setsockopt(zmq.SNDHWM, 100000)
socket.setsockopt(zmq.RCVHWM, 100000)
socket.setsockopt(zmq.LINGER, 0)
socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 300)
```

## High Availability Setup

### 1. Active-Passive Configuration

```yaml
# docker-compose.ha.yml
services:
  keepalived:
    image: osixia/keepalived:latest
    cap_add:
      - NET_ADMIN
    environment:
      - KEEPALIVED_INTERFACE=eth0
      - KEEPALIVED_VIRTUAL_IPS=10.0.0.100
      - KEEPALIVED_PRIORITY=100  # 200 on backup
      - KEEPALIVED_UNICAST_PEERS=10.0.0.11,10.0.0.12
```

### 2. Data Replication

```bash
# Real-time replication with rsync
*/5 * * * * rsync -avz --delete /var/lib/docker/volumes/ backup-server:/backup/mt4/
```

### 3. Load Balancing

```nginx
# HAProxy configuration
frontend mt4_zmq
    bind *:5556
    mode tcp
    default_backend zmq_servers

backend zmq_servers
    mode tcp
    balance roundrobin
    server mt4_1 10.0.0.11:5556 check
    server mt4_2 10.0.0.12:5556 check backup
```

## Monitoring and Alerting

### 1. Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| CPU Usage | 70% | 90% |
| Memory Usage | 80% | 95% |
| Disk Usage | 75% | 90% |
| Message Latency | 5ms | 10ms |
| Message Rate | <1000/s | <100/s |
| Error Rate | >1% | >5% |

### 2. Alerting Configuration

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-ops'
  
receivers:
  - name: 'team-ops'
    slack_configs:
      - api_url: '$SLACK_WEBHOOK_URL'
        channel: '#mt4-alerts'
    pagerduty_configs:
      - routing_key: '$PAGERDUTY_KEY'
```

## Maintenance Procedures

### Daily Tasks
- Check system health dashboard
- Review error logs
- Verify backup completion
- Monitor resource usage

### Weekly Tasks
- Review security logs
- Update system packages
- Test failover procedure
- Clean up old logs

### Monthly Tasks
- Performance review
- Security audit
- Disaster recovery drill
- Update documentation

### Maintenance Mode

```bash
# Enable maintenance mode
docker-compose exec mt4 touch /tmp/maintenance.flag

# Disable maintenance mode
docker-compose exec mt4 rm /tmp/maintenance.flag
```

## Troubleshooting Production Issues

### Common Issues and Solutions

1. **High CPU Usage**
   ```bash
   # Identify process
   docker stats
   docker top <container>
   
   # Increase resources
   docker-compose up -d --scale mt4=2
   ```

2. **Memory Leaks**
   ```bash
   # Monitor memory
   watch -n 1 'docker stats --no-stream'
   
   # Restart with memory limit
   docker-compose restart mt4
   ```

3. **Network Issues**
   ```bash
   # Test connectivity
   docker-compose exec mt4 ping broker.server.com
   
   # Check firewall
   sudo iptables -L -n -v
   ```

## Security Hardening

### 1. Enable AppArmor/SELinux

```bash
# AppArmor profile
sudo aa-enforce /etc/apparmor.d/docker-mt4
```

### 2. Regular Security Scans

```bash
# Weekly security scan
0 2 * * 0 /opt/mt4-docker/scripts/security_scan.sh
```

### 3. Access Control

```bash
# Limit SSH access
AllowUsers mt4admin
PermitRootLogin no
PasswordAuthentication no
```

## Disaster Recovery

See [DISASTER_RECOVERY_GUIDE.md](./DISASTER_RECOVERY_GUIDE.md) for detailed procedures.

## Support and Escalation

### Support Tiers
1. **L1**: System monitoring alerts
2. **L2**: Operations team
3. **L3**: Development team
4. **Vendor**: MT4 platform support

### Escalation Matrix
| Issue Type | Response Time | Escalation |
|------------|--------------|------------|
| Service Down | 5 minutes | L2 → L3 |
| Performance | 30 minutes | L1 → L2 |
| Security | Immediate | L3 + Security Team |

## Conclusion

This guide provides comprehensive instructions for deploying MT4 Docker ZeroMQ in production. Always test changes in staging before applying to production, and maintain regular backups and monitoring.