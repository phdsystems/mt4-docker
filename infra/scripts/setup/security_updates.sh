#!/bin/bash
# Automated Security Updates for MT4 Docker

set -e

# Configuration
UPDATE_LOG="/var/log/mt4-security-updates.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
EMAIL_RECIPIENT="${SECURITY_EMAIL:-security@example.com}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$UPDATE_LOG"
}

# Send notification
send_notification() {
    local level=$1
    local message=$2
    
    # Log the message
    log "$level: $message"
    
    # Send to Slack if webhook is configured
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"MT4 Security Update - $level: $message\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
    
    # Send email if mail is configured
    if command -v mail &> /dev/null && [ -n "$EMAIL_RECIPIENT" ]; then
        echo "$message" | mail -s "MT4 Security Update - $level" "$EMAIL_RECIPIENT" || true
    fi
}

# Check for security updates
check_updates() {
    log "Checking for security updates..."
    
    # Update package lists
    apt-get update -qq
    
    # Check for security updates
    UPDATES=$(apt-get -s upgrade | grep -i security | wc -l)
    
    if [ "$UPDATES" -gt 0 ]; then
        log "Found $UPDATES security updates"
        return 0
    else
        log "No security updates available"
        return 1
    fi
}

# Apply security updates
apply_updates() {
    log "Applying security updates..."
    
    # Create backup point
    if command -v timeshift &> /dev/null; then
        timeshift --create --comments "Before security updates" --tags D || true
    fi
    
    # Apply only security updates
    apt-get -y upgrade -o Dir::Etc::SourceList=/etc/apt/security.sources.list \
        -o Dir::Etc::SourceParts=/dev/null \
        -o APT::Get::List-Cleanup=0
    
    # Log applied updates
    APPLIED=$(grep -E "^$(date +'%Y-%m-%d')" /var/log/apt/history.log | grep Upgrade: | wc -l)
    log "Applied $APPLIED security updates"
    
    return 0
}

# Update Docker images
update_docker_images() {
    log "Checking Docker image updates..."
    
    # List of critical images to update
    IMAGES=(
        "docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
        "docker.elastic.co/logstash/logstash:8.11.0"
        "docker.elastic.co/kibana/kibana:8.11.0"
        "docker.elastic.co/beats/filebeat:8.11.0"
        "docker.elastic.co/beats/metricbeat:8.11.0"
        "prom/prometheus:latest"
        "grafana/grafana:latest"
    )
    
    UPDATED=0
    for IMAGE in "${IMAGES[@]}"; do
        log "Checking $IMAGE..."
        
        # Pull latest image
        if docker pull "$IMAGE" | grep -q "Downloaded newer image"; then
            ((UPDATED++))
            log "Updated $IMAGE"
        fi
    done
    
    if [ "$UPDATED" -gt 0 ]; then
        log "Updated $UPDATED Docker images"
        send_notification "INFO" "Updated $UPDATED Docker images"
        return 0
    else
        log "All Docker images are up to date"
        return 1
    fi
}

# Scan for vulnerabilities
scan_vulnerabilities() {
    log "Scanning for vulnerabilities..."
    
    # Check if trivy is installed
    if ! command -v trivy &> /dev/null; then
        log "Installing Trivy vulnerability scanner..."
        wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add -
        echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list
        apt-get update -qq
        apt-get install -y trivy
    fi
    
    # Scan filesystem
    log "Scanning filesystem vulnerabilities..."
    trivy fs --security-checks vuln --severity HIGH,CRITICAL / > /tmp/trivy-fs.log 2>&1
    
    # Scan Docker images
    log "Scanning Docker image vulnerabilities..."
    docker images --format "{{.Repository}}:{{.Tag}}" | while read -r image; do
        if [[ ! "$image" =~ ^(<none>|scratch).*$ ]]; then
            log "Scanning $image..."
            trivy image --security-checks vuln --severity HIGH,CRITICAL "$image" >> /tmp/trivy-images.log 2>&1
        fi
    done
    
    # Check for critical vulnerabilities
    CRITICAL=$(grep -c "CRITICAL" /tmp/trivy-*.log 2>/dev/null || echo 0)
    HIGH=$(grep -c "HIGH" /tmp/trivy-*.log 2>/dev/null || echo 0)
    
    if [ "$CRITICAL" -gt 0 ]; then
        send_notification "CRITICAL" "Found $CRITICAL critical vulnerabilities!"
        return 1
    elif [ "$HIGH" -gt 0 ]; then
        send_notification "WARNING" "Found $HIGH high severity vulnerabilities"
        return 2
    else
        log "No critical or high severity vulnerabilities found"
        return 0
    fi
}

# Update Python packages
update_python_packages() {
    log "Checking Python package updates..."
    
    # Check if pip-audit is installed
    if ! command -v pip-audit &> /dev/null; then
        pip install pip-audit
    fi
    
    # Audit Python packages
    log "Auditing Python packages for vulnerabilities..."
    pip-audit --desc > /tmp/pip-audit.log 2>&1 || true
    
    VULN_COUNT=$(grep -c "found" /tmp/pip-audit.log 2>/dev/null || echo 0)
    
    if [ "$VULN_COUNT" -gt 0 ]; then
        log "Found $VULN_COUNT vulnerable Python packages"
        
        # Update vulnerable packages
        pip-audit --fix --desc || true
        
        send_notification "INFO" "Updated $VULN_COUNT vulnerable Python packages"
    else
        log "No vulnerable Python packages found"
    fi
}

# Restart services if needed
restart_services() {
    log "Checking if services need restart..."
    
    # Check if needrestart is installed
    if ! command -v needrestart &> /dev/null; then
        apt-get install -y needrestart
    fi
    
    # Check which services need restart
    SERVICES=$(needrestart -b -r l | grep -E "^NEEDRESTART-SVC" | cut -d: -f2)
    
    if [ -n "$SERVICES" ]; then
        log "Services needing restart: $SERVICES"
        
        # Restart services
        for service in $SERVICES; do
            if systemctl is-active --quiet "$service"; then
                log "Restarting $service..."
                systemctl restart "$service" || true
            fi
        done
        
        send_notification "INFO" "Restarted services after updates"
    else
        log "No services need restart"
    fi
}

# Main update process
main() {
    log "=== Starting automated security update process ==="
    
    # Create log directory
    mkdir -p "$(dirname "$UPDATE_LOG")"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log "Error: This script must be run as root"
        exit 1
    fi
    
    # Lock file to prevent concurrent runs
    LOCKFILE="/var/run/mt4-security-updates.lock"
    exec 200>"$LOCKFILE"
    
    if ! flock -n 200; then
        log "Another update process is already running"
        exit 1
    fi
    
    # Track if any updates were applied
    UPDATES_APPLIED=false
    
    # 1. System security updates
    if check_updates; then
        apply_updates && UPDATES_APPLIED=true
    fi
    
    # 2. Docker image updates
    update_docker_images && UPDATES_APPLIED=true
    
    # 3. Python package updates
    update_python_packages && UPDATES_APPLIED=true
    
    # 4. Vulnerability scanning
    scan_vulnerabilities || true
    
    # 5. Restart services if needed
    if [ "$UPDATES_APPLIED" = true ]; then
        restart_services
    fi
    
    # Clean up
    rm -f /tmp/trivy-*.log /tmp/pip-audit.log
    
    log "=== Security update process completed ==="
    
    # Send summary notification
    if [ "$UPDATES_APPLIED" = true ]; then
        send_notification "SUCCESS" "Security updates completed successfully"
    fi
}

# Run main function
main "$@"