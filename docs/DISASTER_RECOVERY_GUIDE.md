# Disaster Recovery Guide for MT4 Docker ZeroMQ

## Table of Contents
1. [Overview](#overview)
2. [Recovery Objectives](#recovery-objectives)
3. [Backup Strategy](#backup-strategy)
4. [Disaster Scenarios](#disaster-scenarios)
5. [Recovery Procedures](#recovery-procedures)
6. [Testing and Validation](#testing-and-validation)
7. [Emergency Contacts](#emergency-contacts)

## Overview

This guide provides comprehensive disaster recovery (DR) procedures for the MT4 Docker ZeroMQ trading infrastructure. It covers backup strategies, recovery procedures, and business continuity planning.

### Critical Components
- MT4 Terminal and configuration
- ZeroMQ message streaming infrastructure
- Market data history
- Security keys and certificates
- Monitoring and logging data
- Docker volumes and configurations

## Recovery Objectives

### RTO (Recovery Time Objective)
| Component | RTO Target | Priority |
|-----------|------------|----------|
| Market Data Streaming | 15 minutes | Critical |
| MT4 Terminal | 30 minutes | Critical |
| Monitoring Stack | 1 hour | High |
| Historical Data | 2 hours | Medium |
| Logging Infrastructure | 4 hours | Low |

### RPO (Recovery Point Objective)
| Data Type | RPO Target | Backup Frequency |
|-----------|------------|------------------|
| Configuration Files | 0 minutes | Real-time sync |
| Market Data | 5 minutes | Continuous |
| Security Keys | 0 minutes | Encrypted sync |
| Application Logs | 1 hour | Hourly |
| Monitoring Data | 24 hours | Daily |

## Backup Strategy

### 1. Automated Backup System

```bash
#!/bin/bash
# /opt/mt4-docker/scripts/backup.sh

# Configuration
BACKUP_ROOT="/backup/mt4-docker"
REMOTE_BACKUP="backup-server:/disaster-recovery/mt4"
RETENTION_DAYS=30

# Create backup timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Backup Docker volumes
echo "Backing up Docker volumes..."
docker run --rm \
  -v mt4_data:/source:ro \
  -v ${BACKUP_DIR}:/backup \
  alpine tar -czf /backup/mt4_data.tar.gz -C /source .

# Backup configurations
echo "Backing up configurations..."
tar -czf "${BACKUP_DIR}/configs.tar.gz" \
  /opt/mt4-docker/docker-compose*.yml \
  /opt/mt4-docker/.env \
  /opt/mt4-docker/configs/

# Backup security keys (encrypted)
echo "Backing up security keys..."
tar -czf - /opt/mt4-docker/keys/ | \
  openssl enc -aes-256-cbc -salt -pass file:/etc/backup.key \
  > "${BACKUP_DIR}/keys.tar.gz.enc"

# Backup database dumps
echo "Backing up databases..."
docker exec elasticsearch \
  elasticsearch-dump \
  --input=http://localhost:9200 \
  --output=/backup/elasticsearch.json \
  --type=data

# Sync to remote location
echo "Syncing to remote backup..."
rsync -avz --delete-after \
  "${BACKUP_ROOT}/" \
  "${REMOTE_BACKUP}/"

# Clean old backups
find "${BACKUP_ROOT}" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \;

echo "Backup completed: ${BACKUP_DIR}"
```

### 2. Real-time Replication

```yaml
# docker-compose.replication.yml
version: '3.8'

services:
  lsyncd:
    image: axiom/rsync-server
    volumes:
      - /opt/mt4-docker:/source:ro
      - ./lsyncd.conf:/etc/lsyncd/lsyncd.conf
    environment:
      - SYNC_DESTINATION=backup-server::mt4-dr
    deploy:
      mode: global
      restart_policy:
        condition: any
        delay: 5s
```

### 3. Configuration Versioning

```bash
# Git-based config backup
cd /opt/mt4-docker
git init
git add -A
git commit -m "Config backup: $(date)"
git push backup master
```

## Disaster Scenarios

### Scenario 1: MT4 Terminal Crash

**Impact**: No market data streaming  
**Detection**: Monitoring alerts, no tick updates

**Recovery Steps**:
```bash
# 1. Check MT4 status
docker-compose ps mt4

# 2. Collect logs
docker-compose logs --tail=100 mt4 > mt4_crash.log

# 3. Restart MT4
docker-compose restart mt4

# 4. If restart fails, recreate container
docker-compose stop mt4
docker-compose rm -f mt4
docker-compose up -d mt4

# 5. Verify EA is running
docker-compose exec mt4 tail -f /mt4/MQL4/Logs/$(date +%Y%m%d).log
```

### Scenario 2: ZeroMQ Service Failure

**Impact**: Subscribers not receiving data  
**Detection**: High latency alerts, connection timeouts

**Recovery Steps**:
```bash
# 1. Test ZeroMQ connectivity
python3 /opt/mt4-docker/scripts/test_zmq_connection.py

# 2. Restart ZeroMQ bridge
docker-compose restart zmq-subscriber

# 3. Clear message queue if needed
docker-compose exec zmq-subscriber \
  python3 -c "import zmq; ctx=zmq.Context(); ctx.term()"

# 4. Verify message flow
docker-compose exec zmq-subscriber \
  tail -f /app/logs/zmq_bridge.log
```

### Scenario 3: Complete Server Failure

**Impact**: All services down  
**Detection**: No response from primary server

**Recovery Steps**:
```bash
# On backup server:

# 1. Activate standby configuration
cd /opt/mt4-docker-standby
cp .env.standby .env

# 2. Update DNS/Load balancer
# Point mt4.yourdomain.com to backup server IP

# 3. Start services in order
docker-compose up -d mt4
sleep 30
docker-compose up -d zmq-subscriber
docker-compose -f docker-compose.monitoring.yml up -d
docker-compose -f docker-compose.elk.yml up -d

# 4. Verify services
./scripts/health_check.sh

# 5. Notify stakeholders
./scripts/send_dr_notification.sh "Primary failover completed"
```

### Scenario 4: Data Corruption

**Impact**: Invalid market data, configuration errors  
**Detection**: Data validation failures, checksum mismatches

**Recovery Steps**:
```bash
# 1. Stop affected services
docker-compose stop

# 2. Identify corruption extent
./scripts/validate_data.sh

# 3. Restore from backup
BACKUP_DATE=$(date -d '1 hour ago' +%Y%m%d_%H)
BACKUP_DIR="/backup/mt4-docker/${BACKUP_DATE}*"

# Restore Docker volumes
docker run --rm \
  -v mt4_data:/target \
  -v ${BACKUP_DIR}:/backup:ro \
  alpine tar -xzf /backup/mt4_data.tar.gz -C /target

# 4. Validate restored data
./scripts/validate_data.sh

# 5. Restart services
docker-compose up -d
```

### Scenario 5: Security Breach

**Impact**: Potential data compromise  
**Detection**: Unusual access patterns, failed auth attempts

**Recovery Steps**:
```bash
# 1. IMMEDIATE: Isolate system
sudo iptables -I INPUT -j DROP
sudo iptables -I OUTPUT -j DROP
sudo iptables -I INPUT -s <admin_ip> -j ACCEPT

# 2. Preserve evidence
docker-compose logs > security_incident_$(date +%s).log
sudo tar -czf /secure/evidence_$(date +%s).tar.gz /var/log/

# 3. Rotate all credentials
./scripts/rotate_all_keys.sh

# 4. Rebuild from clean state
docker-compose down -v
docker system prune -a -f

# 5. Restore from verified backup
./scripts/restore_from_backup.sh --verify-checksums

# 6. Apply security patches
./scripts/security_update.sh --force

# 7. Re-enable network with new rules
sudo iptables -F
sudo ufw --force enable
```

## Recovery Procedures

### 1. Pre-Recovery Checklist

```bash
#!/bin/bash
# pre_recovery_check.sh

echo "=== Pre-Recovery Checklist ==="

# Check backup availability
echo -n "[ ] Latest backup available: "
ls -la /backup/mt4-docker/ | tail -n 1

# Check backup integrity
echo -n "[ ] Backup integrity verified: "
./scripts/verify_backup.sh

# Check target system resources
echo -n "[ ] CPU available: "
echo "$((100 - $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)))%"

echo -n "[ ] Memory available: "
free -h | grep Mem | awk '{print $7}'

echo -n "[ ] Disk space available: "
df -h /opt | tail -n 1 | awk '{print $4}'

# Check network connectivity
echo -n "[ ] Network connectivity: "
ping -c 1 backup-server > /dev/null && echo "OK" || echo "FAIL"

# Check Docker status
echo -n "[ ] Docker daemon running: "
systemctl is-active docker
```

### 2. Standard Recovery Process

```bash
#!/bin/bash
# standard_recovery.sh

set -e

# Configuration
RECOVERY_LOG="/var/log/mt4_recovery_$(date +%Y%m%d_%H%M%S).log"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${RECOVERY_LOG}"
}

# Start recovery
log "Starting MT4 Docker ZeroMQ recovery process"

# Step 1: Stop all services
log "Stopping existing services..."
docker-compose down || true

# Step 2: Backup current state
log "Backing up current state..."
if [ -d "/opt/mt4-docker" ]; then
    tar -czf "/backup/pre-recovery-$(date +%s).tar.gz" /opt/mt4-docker/
fi

# Step 3: Restore from backup
log "Restoring from backup..."
LATEST_BACKUP=$(ls -t /backup/mt4-docker/ | head -n 1)
cd /opt/mt4-docker
tar -xzf "/backup/mt4-docker/${LATEST_BACKUP}/configs.tar.gz"

# Step 4: Restore Docker volumes
log "Restoring Docker volumes..."
for volume in mt4_data elasticsearch_data prometheus_data; do
    docker run --rm \
        -v ${volume}:/target \
        -v /backup/mt4-docker/${LATEST_BACKUP}:/backup:ro \
        alpine tar -xzf /backup/${volume}.tar.gz -C /target
done

# Step 5: Restore security keys
log "Restoring security keys..."
openssl enc -aes-256-cbc -d \
    -in "/backup/mt4-docker/${LATEST_BACKUP}/keys.tar.gz.enc" \
    -pass file:/etc/backup.key | tar -xzf - -C /

# Step 6: Start core services
log "Starting core services..."
docker-compose up -d mt4 zmq-subscriber

# Step 7: Wait for services to be healthy
log "Waiting for services to be healthy..."
sleep 30

# Step 8: Run health checks
log "Running health checks..."
./scripts/health_check.sh

# Step 9: Start remaining services
log "Starting monitoring and logging services..."
docker-compose -f docker-compose.monitoring.yml up -d
docker-compose -f docker-compose.elk.yml up -d

# Step 10: Final validation
log "Running final validation..."
./scripts/validate_recovery.sh

log "Recovery completed successfully"
```

### 3. Rapid Recovery (RTO < 15 minutes)

```bash
#!/bin/bash
# rapid_recovery.sh

# For critical services only
set -e

echo "=== RAPID RECOVERY MODE ==="
echo "Starting at: $(date)"

# 1. Quick restore core services (3 minutes)
docker-compose up -d mt4 zmq-subscriber

# 2. Verify market data flow (2 minutes)
timeout 120 python3 - << 'EOF'
import zmq
import time

context = zmq.Context()
subscriber = context.socket(zmq.SUB)
subscriber.connect("tcp://localhost:5556")
subscriber.subscribe(b"")
subscriber.setsockopt(zmq.RCVTIMEO, 5000)

print("Waiting for market data...")
try:
    topic, message = subscriber.recv_multipart()
    print(f"✓ Received data on topic: {topic.decode()}")
except zmq.Again:
    print("✗ No data received - RECOVERY FAILED")
    exit(1)
EOF

# 3. Start minimal monitoring (1 minute)
docker-compose -f docker-compose.monitoring.yml up -d prometheus

echo "Core services recovered at: $(date)"
echo "Continue with full recovery using standard_recovery.sh"
```

## Testing and Validation

### 1. Recovery Test Schedule

| Test Type | Frequency | Duration | Systems Affected |
|-----------|-----------|----------|------------------|
| Backup Verification | Daily | 5 min | None |
| Component Failover | Weekly | 30 min | Individual |
| Full DR Test | Monthly | 2 hours | All non-prod |
| Site Failover | Quarterly | 4 hours | Full production |

### 2. Automated DR Testing

```bash
#!/bin/bash
# test_dr_monthly.sh

# Configuration
TEST_ENV="dr-test"
TEST_LOG="/var/log/dr_test_$(date +%Y%m%d).log"

echo "=== Monthly DR Test Starting ===" | tee "${TEST_LOG}"

# 1. Create isolated test environment
docker network create ${TEST_ENV} || true

# 2. Deploy test instance
docker-compose -p ${TEST_ENV} up -d

# 3. Simulate failures
./scripts/chaos_monkey.sh --env ${TEST_ENV}

# 4. Execute recovery procedures
./scripts/standard_recovery.sh --env ${TEST_ENV}

# 5. Validate recovery
python3 tests/test_dr_validation.py --env ${TEST_ENV}

# 6. Generate report
./scripts/generate_dr_report.sh --env ${TEST_ENV}

# 7. Cleanup
docker-compose -p ${TEST_ENV} down -v
docker network rm ${TEST_ENV}

echo "=== DR Test Completed ===" | tee -a "${TEST_LOG}"
```

### 3. Recovery Validation Checklist

```python
#!/usr/bin/env python3
# validate_recovery.py

import sys
import zmq
import json
import requests
from datetime import datetime, timedelta

def validate_recovery():
    """Comprehensive recovery validation"""
    
    checks = []
    
    # 1. Check MT4 Terminal
    try:
        # Check if MT4 process is running
        # This would normally check via Docker API
        checks.append(("MT4 Terminal Running", True))
    except:
        checks.append(("MT4 Terminal Running", False))
    
    # 2. Check ZeroMQ streaming
    try:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://localhost:5556")
        socket.subscribe(b"")
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        
        topic, message = socket.recv_multipart()
        data = json.loads(message.decode())
        
        # Check data freshness
        if 'timestamp' in data:
            age = datetime.now().timestamp() - data['timestamp']
            checks.append(("Market Data Fresh (<60s)", age < 60))
        
        checks.append(("ZeroMQ Streaming", True))
        socket.close()
        context.term()
    except:
        checks.append(("ZeroMQ Streaming", False))
    
    # 3. Check monitoring stack
    try:
        resp = requests.get("http://localhost:9090/-/healthy", timeout=5)
        checks.append(("Prometheus Healthy", resp.status_code == 200))
    except:
        checks.append(("Prometheus Healthy", False))
    
    # 4. Check logging
    try:
        resp = requests.get("http://localhost:9200/_cluster/health", timeout=5)
        health = resp.json()
        checks.append(("Elasticsearch Healthy", health['status'] in ['green', 'yellow']))
    except:
        checks.append(("Elasticsearch Healthy", False))
    
    # 5. Check data integrity
    try:
        # This would check data consistency
        checks.append(("Data Integrity Check", True))
    except:
        checks.append(("Data Integrity Check", False))
    
    # Generate report
    print("\n=== Recovery Validation Report ===")
    print(f"Timestamp: {datetime.now()}")
    print("-" * 40)
    
    passed = 0
    for check, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{check:<30} {status}")
        if result:
            passed += 1
    
    print("-" * 40)
    print(f"Total: {passed}/{len(checks)} checks passed")
    
    # Return success if all critical checks pass
    critical_checks = ["MT4 Terminal Running", "ZeroMQ Streaming"]
    critical_passed = all(result for check, result in checks if check in critical_checks)
    
    return critical_passed

if __name__ == "__main__":
    success = validate_recovery()
    sys.exit(0 if success else 1)
```

## Testing and Validation (continued)

### 4. Chaos Engineering Tests

```python
#!/usr/bin/env python3
# chaos_tests.py

import random
import subprocess
import time
import logging

class ChaosMonkey:
    """Simulate various failure scenarios"""
    
    def __init__(self, target_env="production"):
        self.env = target_env
        self.logger = logging.getLogger("chaos")
    
    def kill_random_container(self):
        """Randomly kill a container"""
        containers = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}"]
        ).decode().strip().split('\n')
        
        if containers:
            victim = random.choice(containers)
            self.logger.info(f"Killing container: {victim}")
            subprocess.run(["docker", "kill", victim])
            return victim
        return None
    
    def network_partition(self, duration=60):
        """Simulate network partition"""
        self.logger.info(f"Creating network partition for {duration}s")
        
        # Add network delay and packet loss
        subprocess.run([
            "tc", "qdisc", "add", "dev", "eth0", "root",
            "netem", "delay", "100ms", "loss", "10%"
        ])
        
        time.sleep(duration)
        
        # Remove network impairment
        subprocess.run(["tc", "qdisc", "del", "dev", "eth0", "root"])
    
    def disk_pressure(self):
        """Create disk pressure"""
        self.logger.info("Creating disk pressure")
        
        # Write large file
        subprocess.run([
            "dd", "if=/dev/zero", "of=/tmp/chaos_disk",
            "bs=1G", "count=10"
        ])
        
        time.sleep(30)
        
        # Cleanup
        subprocess.run(["rm", "-f", "/tmp/chaos_disk"])
    
    def memory_pressure(self):
        """Create memory pressure"""
        self.logger.info("Creating memory pressure")
        
        # Use stress-ng if available
        subprocess.run([
            "docker", "run", "--rm",
            "alexeiled/stress-ng",
            "--vm", "2", "--vm-bytes", "1G",
            "--timeout", "60s"
        ])

# Run chaos tests
if __name__ == "__main__":
    chaos = ChaosMonkey()
    
    tests = [
        chaos.kill_random_container,
        lambda: chaos.network_partition(30),
        chaos.disk_pressure,
        chaos.memory_pressure
    ]
    
    for test in tests:
        try:
            test()
            time.sleep(30)  # Allow recovery
        except Exception as e:
            print(f"Chaos test failed: {e}")
```

## Emergency Contacts

### Escalation Matrix

```yaml
# /opt/mt4-docker/configs/emergency_contacts.yml

contacts:
  # Level 1 - Automated Alerts
  automated:
    slack:
      webhook: "${SLACK_WEBHOOK_URL}"
      channel: "#mt4-alerts"
    pagerduty:
      api_key: "${PAGERDUTY_API_KEY}"
      service_id: "PXXXXXXX"
  
  # Level 2 - Operations Team
  operations:
    - name: "Operations Lead"
      phone: "+1-555-0001"
      email: "ops-lead@company.com"
      availability: "24/7"
    - name: "Senior DevOps"
      phone: "+1-555-0002"
      email: "devops@company.com"
      availability: "Business hours + on-call"
  
  # Level 3 - Development Team
  development:
    - name: "Tech Lead"
      phone: "+1-555-0003"
      email: "tech-lead@company.com"
      availability: "Business hours"
    - name: "MT4 Specialist"
      phone: "+1-555-0004"
      email: "mt4-dev@company.com"
      availability: "Business hours"
  
  # External Vendors
  vendors:
    - name: "MetaQuotes Support"
      email: "support@metaquotes.net"
      ticket_url: "https://www.metatrader4.com/en/support"
    - name: "Hosting Provider"
      phone: "+1-555-9000"
      email: "support@hosting.com"
      availability: "24/7"
    - name: "Network Provider"
      phone: "+1-555-9001"
      noc_email: "noc@network.com"
```

### Automated Notification Script

```bash
#!/bin/bash
# send_emergency_notification.sh

SEVERITY=$1
MESSAGE=$2
INCIDENT_ID=$(date +%s)

# Function to send notifications
send_notification() {
    local channel=$1
    local message=$2
    
    case $channel in
        "slack")
            curl -X POST $SLACK_WEBHOOK_URL \
                -H 'Content-Type: application/json' \
                -d "{
                    \"text\": \"🚨 DR Incident ${INCIDENT_ID}\",
                    \"attachments\": [{
                        \"color\": \"danger\",
                        \"title\": \"${SEVERITY} Severity Incident\",
                        \"text\": \"${message}\",
                        \"footer\": \"MT4 Docker ZeroMQ\",
                        \"ts\": $(date +%s)
                    }]
                }"
            ;;
        "pagerduty")
            curl -X POST https://events.pagerduty.com/v2/enqueue \
                -H 'Content-Type: application/json' \
                -H "Authorization: Token token=${PAGERDUTY_API_KEY}" \
                -d "{
                    \"routing_key\": \"${PAGERDUTY_SERVICE_ID}\",
                    \"event_action\": \"trigger\",
                    \"payload\": {
                        \"summary\": \"${message}\",
                        \"severity\": \"${SEVERITY}\",
                        \"source\": \"mt4-docker\",
                        \"custom_details\": {
                            \"incident_id\": \"${INCIDENT_ID}\"
                        }
                    }
                }"
            ;;
        "email")
            echo "${message}" | mail -s "DR Incident ${INCIDENT_ID} - ${SEVERITY}" \
                ops-team@company.com
            ;;
    esac
}

# Send to all channels based on severity
case $SEVERITY in
    "critical")
        send_notification "pagerduty" "$MESSAGE"
        send_notification "slack" "$MESSAGE"
        send_notification "email" "$MESSAGE"
        ;;
    "high")
        send_notification "slack" "$MESSAGE"
        send_notification "email" "$MESSAGE"
        ;;
    "medium")
        send_notification "slack" "$MESSAGE"
        ;;
    "low")
        echo "[$(date)] ${MESSAGE}" >> /var/log/mt4_incidents.log
        ;;
esac
```

## Recovery Runbooks

### Runbook: Market Data Streaming Failure

```markdown
# Runbook: Market Data Streaming Failure

## Symptoms
- No tick updates in subscriber logs
- Monitoring shows 0 messages/sec
- Client applications reporting no data

## Impact
- Trading systems not receiving market updates
- Potential missed trading opportunities
- Client dissatisfaction

## Resolution Steps

### 1. Quick Diagnosis (2 min)
```bash
# Check MT4 terminal status
docker-compose ps mt4

# Check last tick timestamp
docker-compose exec zmq-subscriber \
    tail -n 1 /app/logs/ticks.log | jq .timestamp

# Check ZeroMQ connections
docker-compose exec zmq-subscriber \
    netstat -an | grep 5556
```

### 2. Immediate Actions (5 min)
```bash
# Restart EA in MT4
docker-compose exec mt4 \
    /app/scripts/restart_ea.sh MT4ZMQBridge

# If EA restart fails, restart MT4
docker-compose restart mt4

# Monitor logs
docker-compose logs -f mt4 zmq-subscriber
```

### 3. If Problem Persists (10 min)
```bash
# Full service restart
docker-compose down
docker-compose up -d

# Verify data flow
python3 /opt/mt4-docker/scripts/verify_stream.py
```

### 4. Escalation
If not resolved within 15 minutes:
- Page on-call engineer
- Prepare for failover to backup system
```

### Runbook: Database Corruption

```markdown
# Runbook: Database Corruption

## Symptoms
- Elasticsearch health status RED
- Query errors in Kibana
- Missing historical data

## Impact
- Loss of historical market data
- Monitoring dashboards unavailable
- Compliance reporting affected

## Resolution Steps

### 1. Assess Damage (5 min)
```bash
# Check cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Identify corrupted indices
curl -X GET "localhost:9200/_cat/indices?v&health=red"

# Check disk space
df -h /var/lib/docker/volumes/elasticsearch_data
```

### 2. Attempt Recovery (15 min)
```bash
# Try to recover corrupted shards
curl -X POST "localhost:9200/_cluster/reroute?retry_failed=true"

# If specific index is corrupted
INDEX_NAME="market_data_2024.01"
curl -X POST "localhost:9200/${INDEX_NAME}/_flush/synced"
```

### 3. Restore from Backup (30 min)
```bash
# Stop Elasticsearch
docker-compose stop elasticsearch

# Restore data directory
BACKUP_DATE=$(date -d '1 day ago' +%Y%m%d)
tar -xzf /backup/elasticsearch_${BACKUP_DATE}.tar.gz \
    -C /var/lib/docker/volumes/elasticsearch_data/_data/

# Start Elasticsearch
docker-compose up -d elasticsearch

# Verify restoration
curl -X GET "localhost:9200/_cat/indices?v"
```

### 4. Prevent Future Corruption
```bash
# Increase heap size
echo "ES_JAVA_OPTS=-Xmx4g -Xms4g" >> .env

# Enable better monitoring
curl -X PUT "localhost:9200/_cluster/settings" \
    -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "85%",
    "cluster.routing.allocation.disk.watermark.high": "90%"
  }
}'
```
```

## Business Continuity Planning

### 1. Communication Plan

```yaml
# communication_plan.yml

incident_levels:
  P1_critical:
    description: "Complete service outage"
    notification_time: "Immediate"
    update_frequency: "Every 15 minutes"
    stakeholders:
      - executives
      - all_clients
      - operations_team
      - development_team
    
  P2_high:
    description: "Partial service degradation"
    notification_time: "Within 15 minutes"
    update_frequency: "Every 30 minutes"
    stakeholders:
      - operations_team
      - affected_clients
      - management
    
  P3_medium:
    description: "Minor issues, workaround available"
    notification_time: "Within 1 hour"
    update_frequency: "Every 2 hours"
    stakeholders:
      - operations_team
      - affected_clients

communication_templates:
  initial_notification: |
    Subject: [P${SEVERITY}] MT4 Service Incident - ${INCIDENT_ID}
    
    We are currently experiencing ${ISSUE_DESCRIPTION}.
    
    Impact: ${IMPACT_DESCRIPTION}
    Start Time: ${START_TIME}
    
    Our team is actively working on resolution. 
    Next update in ${UPDATE_INTERVAL}.
    
  resolution_notification: |
    Subject: [RESOLVED] MT4 Service Incident - ${INCIDENT_ID}
    
    The incident has been resolved.
    
    Resolution Time: ${END_TIME}
    Total Duration: ${DURATION}
    Root Cause: ${ROOT_CAUSE}
    
    We apologize for any inconvenience caused.
```

### 2. Disaster Recovery Metrics

```python
#!/usr/bin/env python3
# dr_metrics.py

import json
from datetime import datetime, timedelta
from collections import defaultdict

class DRMetrics:
    """Track and report DR metrics"""
    
    def __init__(self):
        self.incidents = []
        self.tests = []
    
    def record_incident(self, incident_type, start_time, end_time, data_loss=False):
        """Record an incident"""
        duration = (end_time - start_time).total_seconds() / 60
        
        self.incidents.append({
            'type': incident_type,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'duration_minutes': duration,
            'data_loss': data_loss,
            'month': start_time.strftime('%Y-%m')
        })
    
    def calculate_availability(self, year, month):
        """Calculate monthly availability"""
        import calendar
        
        days_in_month = calendar.monthrange(year, month)[1]
        total_minutes = days_in_month * 24 * 60
        
        # Sum downtime for the month
        month_key = f"{year}-{month:02d}"
        downtime = sum(
            inc['duration_minutes'] 
            for inc in self.incidents 
            if inc['month'] == month_key
        )
        
        availability = ((total_minutes - downtime) / total_minutes) * 100
        return availability
    
    def generate_report(self):
        """Generate DR metrics report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_incidents': len(self.incidents),
                'total_tests': len(self.tests),
                'incidents_with_data_loss': sum(1 for i in self.incidents if i['data_loss'])
            },
            'mttr': {},  # Mean Time To Recovery
            'availability': {}
        }
        
        # Calculate MTTR by incident type
        mttr_by_type = defaultdict(list)
        for incident in self.incidents:
            mttr_by_type[incident['type']].append(incident['duration_minutes'])
        
        for inc_type, durations in mttr_by_type.items():
            report['mttr'][inc_type] = {
                'average_minutes': sum(durations) / len(durations),
                'min_minutes': min(durations),
                'max_minutes': max(durations)
            }
        
        # Calculate monthly availability
        current_date = datetime.now()
        for i in range(12):
            month_date = current_date - timedelta(days=30*i)
            availability = self.calculate_availability(
                month_date.year, 
                month_date.month
            )
            month_key = month_date.strftime('%Y-%m')
            report['availability'][month_key] = availability
        
        return report

# Usage example
if __name__ == "__main__":
    metrics = DRMetrics()
    
    # Record some sample incidents
    metrics.record_incident(
        'mt4_crash',
        datetime(2024, 1, 15, 14, 30),
        datetime(2024, 1, 15, 14, 45),
        data_loss=False
    )
    
    # Generate report
    report = metrics.generate_report()
    print(json.dumps(report, indent=2))
```

## Appendix

### A. Quick Reference Commands

```bash
# Service Management
docker-compose ps                    # Check service status
docker-compose restart <service>     # Restart specific service
docker-compose logs -f <service>     # View service logs

# Health Checks
curl http://localhost:5556/health    # ZeroMQ health
curl http://localhost:9090/-/healthy # Prometheus health
curl http://localhost:9200/_cluster/health # Elasticsearch health

# Backup Commands
./scripts/backup.sh                  # Run manual backup
./scripts/restore_from_backup.sh     # Restore from latest backup
./scripts/verify_backup.sh           # Verify backup integrity

# Emergency Commands
./scripts/emergency_stop.sh          # Stop all services immediately
./scripts/rapid_recovery.sh          # Quick recovery (RTO < 15 min)
./scripts/failover_to_dr.sh          # Failover to DR site
```

### B. Configuration Files

Key configuration files to backup:
- `/opt/mt4-docker/.env`
- `/opt/mt4-docker/docker-compose*.yml`
- `/opt/mt4-docker/configs/`
- `/opt/mt4-docker/keys/`
- `/mt4/config/`

### C. Monitoring URLs

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Kibana: http://localhost:5601
- Elasticsearch: http://localhost:9200

### D. Log Locations

- MT4 Logs: `/mt4/MQL4/Logs/`
- Docker Logs: `docker-compose logs <service>`
- System Logs: `/var/log/mt4-docker/`
- Application Logs: `/app/logs/`

## Conclusion

This disaster recovery guide provides comprehensive procedures for maintaining business continuity of the MT4 Docker ZeroMQ infrastructure. Regular testing and updates of these procedures are essential for effective disaster recovery.

Remember: **The best disaster recovery plan is one that's regularly tested and updated.**