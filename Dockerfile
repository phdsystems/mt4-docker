FROM ubuntu:20.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install all required packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    software-properties-common \
    winbind \
    xvfb \
    x11vnc \
    supervisor \
    gettext-base \
    procps \
    net-tools \
    iputils-ping \
    iproute2 \
    curl \
    nano \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Add Wine repository and install Wine
RUN dpkg --add-architecture i386 \
    && wget -qO - https://dl.winehq.org/wine-builds/winehq.key | apt-key add - \
    && add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ focal main' \
    && apt-get update \
    && apt-get install -y winehq-stable \
    && rm -rf /var/lib/apt/lists/*

# Set Wine environment
ENV WINEARCH=win32
ENV WINEPREFIX=/root/.wine
ENV DISPLAY=:99
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Initialize Wine
RUN winecfg || true

# Create MT4 directory structure
RUN mkdir -p /mt4/MQL4/Experts \
    /mt4/MQL4/Indicators \
    /mt4/MQL4/Scripts \
    /mt4/MQL4/Files \
    /mt4/MQL4/Logs \
    /mt4/MQL4/Profiles/Templates \
    /mt4/MQL4/Profiles/Default \
    /mt4/config \
    /mt4/logs

# Set working directory
WORKDIR /mt4

# Create supervisord configuration
RUN echo '[supervisord]' > /etc/supervisor/conf.d/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'logfile=/mt4/logs/supervisord.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'loglevel=info' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:xvfb]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/usr/bin/Xvfb :99 -screen 0 1024x768x16 -ac' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=100' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/mt4/logs/xvfb.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile=/mt4/logs/xvfb.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:x11vnc]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/usr/bin/x11vnc -display :99 -nopw -listen 0.0.0.0 -forever -shared' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=200' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/mt4/logs/x11vnc.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile=/mt4/logs/x11vnc.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:mt4]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/mt4/start_mt4.sh' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'environment=DISPLAY=":99",WINEARCH="win32",WINEPREFIX="/root/.wine"' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=300' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/mt4/logs/mt4.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stderr_logfile=/mt4/logs/mt4.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startsecs=10' >> /etc/supervisor/conf.d/supervisord.conf

# Create startup script
RUN echo '#!/bin/bash' > /mt4/start_mt4.sh && \
    echo 'echo "[$(date)] Starting MT4..."' >> /mt4/start_mt4.sh && \
    echo 'sleep 5' >> /mt4/start_mt4.sh && \
    echo 'export DISPLAY=:99' >> /mt4/start_mt4.sh && \
    echo 'export WINEPREFIX=/root/.wine' >> /mt4/start_mt4.sh && \
    echo 'export WINEARCH=win32' >> /mt4/start_mt4.sh && \
    echo 'cd /mt4' >> /mt4/start_mt4.sh && \
    echo 'if [ ! -f "/mt4/terminal.exe" ]; then' >> /mt4/start_mt4.sh && \
    echo '    echo "ERROR: terminal.exe not found"' >> /mt4/start_mt4.sh && \
    echo '    echo "Please copy terminal.exe to the container"' >> /mt4/start_mt4.sh && \
    echo '    sleep infinity' >> /mt4/start_mt4.sh && \
    echo 'fi' >> /mt4/start_mt4.sh && \
    echo 'if [ -f "/mt4/config/server-config.ini" ]; then' >> /mt4/start_mt4.sh && \
    echo '    envsubst < /mt4/config/server-config.ini > /mt4/config.ini' >> /mt4/start_mt4.sh && \
    echo 'fi' >> /mt4/start_mt4.sh && \
    echo 'find /mt4/MQL4 -name "*.mq4" -exec touch {} \;' >> /mt4/start_mt4.sh && \
    echo 'exec wine /mt4/terminal.exe /portable /config:config.ini' >> /mt4/start_mt4.sh && \
    chmod +x /mt4/start_mt4.sh

# Create test script
RUN echo '#!/bin/bash' > /mt4/test_system.sh && \
    echo 'echo "System Test"' >> /mt4/test_system.sh && \
    echo 'echo "==========="' >> /mt4/test_system.sh && \
    echo 'echo ""' >> /mt4/test_system.sh && \
    echo 'echo "1. Network connectivity:"' >> /mt4/test_system.sh && \
    echo 'ping -c 1 google.com && echo "✓ Network OK" || echo "✗ Network failed"' >> /mt4/test_system.sh && \
    echo 'echo ""' >> /mt4/test_system.sh && \
    echo 'echo "2. Wine installation:"' >> /mt4/test_system.sh && \
    echo 'wine --version && echo "✓ Wine OK" || echo "✗ Wine failed"' >> /mt4/test_system.sh && \
    echo 'echo ""' >> /mt4/test_system.sh && \
    echo 'echo "3. MT4 executable:"' >> /mt4/test_system.sh && \
    echo '[ -f "/mt4/terminal.exe" ] && echo "✓ terminal.exe found" || echo "✗ terminal.exe missing"' >> /mt4/test_system.sh && \
    chmod +x /mt4/test_system.sh

# Create health check
RUN echo '#!/bin/bash' > /mt4/health_check.sh && \
    echo 'pgrep -f terminal.exe > /dev/null || exit 1' >> /mt4/health_check.sh && \
    chmod +x /mt4/health_check.sh

# Copy configuration files
COPY MQL4/Profiles/Templates/default.tpl /mt4/MQL4/Profiles/Templates/default.tpl
COPY config/server-config.ini /mt4/config/server-config.ini

# Note: terminal.exe should be copied using docker cp after container is running
# This avoids build-time errors with wildcard patterns

# Expose VNC port
EXPOSE 5900

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD /mt4/health_check.sh

# Default command
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
