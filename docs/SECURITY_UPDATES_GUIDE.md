# Automated Security Updates Guide

## Overview

This guide describes the automated security update system for the MT4 Docker project. The system continuously monitors for vulnerabilities and can automatically apply security patches to keep the environment secure.

## 🛡️ Security Features

### 1. **Vulnerability Scanning**
- System package vulnerabilities
- Docker image vulnerabilities
- Python package vulnerabilities
- Configuration security audit

### 2. **Automated Updates**
- Critical security patches
- Zero-day vulnerability response
- Scheduled maintenance windows
- Rollback capabilities

### 3. **Monitoring & Alerts**
- Real-time vulnerability detection
- Security event logging
- Slack/Email notifications
- ELK integration

### 4. **Compliance**
- CIS benchmark checks
- PCI-DSS compliance
- NIST framework alignment
- Audit trail maintenance

## 🚀 Quick Start

### 1. Deploy Security Updater

```bash
# Start security monitoring
docker-compose -f docker-compose.security.yml up -d

# Check status
docker-compose -f docker-compose.security.yml ps

# View logs
docker-compose -f docker-compose.security.yml logs -f security-updater
```

### 2. Manual Security Check

```bash
# Run immediate security scan
docker-compose -f docker-compose.security.yml exec security-updater check

# Run vulnerability monitor
docker-compose -f docker-compose.security.yml exec security-updater monitor
```

### 3. Install as System Service

```bash
# Copy systemd files
sudo cp config/systemd/mt4-security-updates.* /etc/systemd/system/

# Enable service
sudo systemctl enable mt4-security-updates.timer
sudo systemctl start mt4-security-updates.timer

# Check status
sudo systemctl status mt4-security-updates.timer
```

## 🔧 Configuration

### Environment Variables

```bash
# Create .env file
cat > .env << EOF
# Slack webhook for notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email for security alerts
SECURITY_EMAIL=security@yourcompany.com

# Auto-update settings
AUTO_UPDATE_ENABLED=false
AUTO_UPDATE_CRITICAL_ONLY=true
EOF
```

### Security Configuration

Edit `config/security/security.json`:

```json
{
  "auto_update": {
    "enabled": true,
    "critical_only": true,
    "packages": {
      "system": ["openssl", "openssh-*"],
      "python": ["cryptography", "requests"],
      "docker_images": ["elasticsearch", "kibana"]
    }
  },
  "notifications": {
    "enabled": true,
    "webhook_url": "${SLACK_WEBHOOK_URL}",
    "thresholds": {
      "critical": 1,
      "high": 5
    }
  }
}
```

## 📊 Security Monitoring

### 1. **Vulnerability Dashboard**

Access Trivy dashboard at http://localhost:8080

### 2. **ELK Integration**

View security logs in Kibana:
- Go to http://localhost:5601
- Search: `tags:security`
- Filter: `event_type:security`

### 3. **Security Reports**

Reports are generated at:
- JSON: `/app/logs/security-report.json`
- HTML: `/app/logs/security-report.html`

## 🔍 Vulnerability Scanning

### System Packages

```bash
# Scan system packages
docker exec mt4_security_updater trivy fs /

# Check specific package
apt-cache policy openssl
```

### Docker Images

```bash
# Scan all images
docker exec mt4_security_updater /app/scripts/security_updates.sh

# Scan specific image
trivy image mt4-docker:latest
```

### Python Packages

```bash
# Audit Python packages
docker exec mt4_security_updater pip-audit

# Check specific package
safety check --json
```

## 🚨 Alert Configuration

### Slack Notifications

```json
{
  "notifications": {
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK",
    "channels": {
      "critical": "#security-critical",
      "high": "#security-alerts",
      "info": "#security-info"
    }
  }
}
```

### Email Alerts

```json
{
  "notifications": {
    "email": {
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "alerts@company.com",
      "smtp_password": "${SMTP_PASSWORD}",
      "recipients": ["security@company.com", "ops@company.com"]
    }
  }
}
```

## 📋 Update Policies

### Critical Updates

Applied immediately when:
- CVSS score >= 9.0
- Actively exploited vulnerability
- Zero-day vulnerability

### High Priority Updates

Applied within 24 hours when:
- CVSS score >= 7.0
- Network-accessible service
- Authentication bypass

### Standard Updates

Applied during maintenance window:
- Weekly schedule
- Low-impact vulnerabilities
- Feature updates

## 🔄 Rollback Procedures

### Automatic Rollback

Triggered when:
- Service fails to start after update
- Health check fails
- Critical errors detected

### Manual Rollback

```bash
# List snapshots
docker exec mt4_security_updater timeshift --list

# Restore snapshot
docker exec mt4_security_updater timeshift --restore --snapshot '2024-01-15_03-00-00'
```

## 📊 Security Metrics

### Key Performance Indicators

1. **Mean Time to Patch (MTTP)**
   - Target: < 24 hours for critical
   - Measure: Time from CVE publication to patch

2. **Vulnerability Exposure Window**
   - Target: Zero critical vulnerabilities
   - Measure: Number of unpatched vulnerabilities

3. **Update Success Rate**
   - Target: > 99%
   - Measure: Successful updates / total updates

### Monitoring Queries

```kuery
# Critical vulnerabilities
event_type:security AND severity:CRITICAL

# Failed updates
event_type:update_failed

# Security scan results
event_type:scan_complete
```

## 🧪 Testing

### Test Security Updates

```bash
# Dry run mode
docker exec mt4_security_updater /app/scripts/security_updates.sh --dry-run

# Test notifications
docker exec mt4_security_updater /app/scripts/security_monitor.py --test-alerts
```

### Vulnerability Injection

```bash
# Install vulnerable package for testing
docker exec mt4_test pip install requests==2.6.0

# Run scan
docker exec mt4_security_updater pip-audit

# Verify detection and remediation
```

## 🚀 Best Practices

### 1. **Regular Scanning**
- Automated scans every 6 hours
- Manual scans before deployments
- Post-update verification scans

### 2. **Update Windows**
- Define maintenance windows
- Stagger updates across services
- Test in staging first

### 3. **Documentation**
- Document all manual interventions
- Maintain change log
- Update runbooks regularly

### 4. **Access Control**
- Limit who can disable auto-updates
- Audit all configuration changes
- Use separate credentials for updates

## 🔐 Security Hardening

### Container Security

```dockerfile
# Run as non-root where possible
USER security-scanner

# Read-only root filesystem
docker run --read-only ...

# Drop capabilities
docker run --cap-drop=ALL ...
```

### Network Security

```yaml
# Isolate security scanner
networks:
  security_net:
    internal: true
```

## 📚 Compliance Reports

### Generate Compliance Report

```bash
# CIS Benchmark
docker exec mt4_security_updater lynis audit system

# Custom compliance check
docker exec mt4_security_updater /app/scripts/compliance_check.sh
```

### Audit Trail

All security events are logged with:
- Timestamp
- User/System identity
- Action performed
- Result
- Justification

## 🆘 Troubleshooting

### Common Issues

1. **Updates Failing**
   ```bash
   # Check logs
   docker logs mt4_security_updater
   
   # Verify connectivity
   docker exec mt4_security_updater apt-get update
   ```

2. **Notifications Not Working**
   ```bash
   # Test webhook
   curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"Test"}'
   
   # Check ELK connection
   docker exec mt4_security_updater nc -zv logstash 5000
   ```

3. **High Memory Usage**
   ```yaml
   # Limit resources
   deploy:
     resources:
       limits:
         memory: 512M
   ```

## 🎯 Security Update Checklist

- [ ] Security scanner deployed
- [ ] Notifications configured
- [ ] Auto-update policy defined
- [ ] Maintenance windows scheduled
- [ ] Rollback procedures tested
- [ ] Monitoring dashboards created
- [ ] Compliance requirements met
- [ ] Documentation updated
- [ ] Team trained on procedures
- [ ] Incident response plan ready

The automated security update system ensures your MT4 Docker environment stays secure with minimal manual intervention while maintaining stability and compliance.