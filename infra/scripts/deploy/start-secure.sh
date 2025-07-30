#!/bin/bash
set -euo pipefail

# Security: Don't echo sensitive information
set +x

# Function to read secrets securely
read_secret() {
    local secret_name=$1
    local secret_file="/run/secrets/${secret_name}"
    
    if [ -f "$secret_file" ]; then
        cat "$secret_file" | tr -d '\n'
    else
        echo "Error: Secret $secret_name not found" >&2
        exit 1
    fi
}

# Read credentials from Docker secrets
MT4_LOGIN=$(read_secret "mt4_login")
MT4_PASSWORD=$(read_secret "mt4_password")
VNC_PASSWORD=$(read_secret "vnc_password")

# Validate inputs
if [ -z "$MT4_LOGIN" ] || [ -z "$MT4_PASSWORD" ] || [ -z "$VNC_PASSWORD" ]; then
    echo "Error: Required secrets not provided" >&2
    exit 1
fi

# Security: Ensure proper ownership
if [ "$(id -u)" = "0" ]; then
    echo "Error: Running as root is not allowed" >&2
    exit 1
fi

# Create required directories
mkdir -p /mt4/logs /mt4/data /tmp/supervisor

# Set secure VNC password
x11vnc -storepasswd "$VNC_PASSWORD" /home/mt4user/.vnc/passwd
chmod 600 /home/mt4user/.vnc/passwd

# Configure terminal.ini with credentials
cat > /mt4/config/terminal.ini << EOF
[Common]
Login=$MT4_LOGIN
Password=$MT4_PASSWORD
Server=$MT4_SERVER
AutoConfiguration=true
EOF

# Set restrictive permissions
chmod 600 /mt4/config/terminal.ini

# Clear sensitive variables from memory
unset MT4_PASSWORD
unset VNC_PASSWORD

# Start supervisord as non-root user
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf