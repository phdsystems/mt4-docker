FROM ubuntu:20.04

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
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
    nano \
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

# Initialize Wine
RUN winecfg || true

# Create MT4 directory
WORKDIR /mt4

# Create necessary directories
RUN mkdir -p /mt4/MQL4/Experts \
    /mt4/MQL4/Indicators \
    /mt4/MQL4/Scripts \
    /mt4/MQL4/Logs \
    /mt4/MQL4/Files \
    /mt4/MQL4/Profiles/Templates \
    /mt4/MQL4/Profiles/Default \
    /mt4/config \
    /mt4/logs

# Copy configuration files
COPY config/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY infra/scripts/deploy/start.sh /start.sh
COPY scripts/auto-compile.sh /auto-compile.sh
COPY config/mt4/server-config.ini /mt4/config/server-config.ini

# Copy MT4 files
COPY terminal.exe /mt4/terminal.exe
COPY MQL4/ /mt4/MQL4/

# Make scripts executable
RUN chmod +x /start.sh /auto-compile.sh

# Expose VNC port for debugging (optional)
EXPOSE 5900

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
