#!/bin/bash

# MT4 Demo Account Setup Helper
# Helps configure demo account credentials

echo "MT4 Demo Account Setup Helper"
echo "============================"
echo ""

# Popular demo servers
echo "Popular MT4 Demo Servers:"
echo "1. MetaQuotes-Demo (Built-in)"
echo "2. ICMarkets-Demo02"
echo "3. Pepperstone-Demo01"
echo "4. Exness-Demo"
echo "5. XM.COM-Demo 3"
echo "6. FBS-Demo"
echo "7. Alpari-Demo"
echo "8. RoboForex-Demo"
echo "9. Custom server"
echo ""

read -p "Select server (1-9): " server_choice

case $server_choice in
    1) MT4_SERVER="MetaQuotes-Demo" ;;
    2) MT4_SERVER="ICMarkets-Demo02" ;;
    3) MT4_SERVER="Pepperstone-Demo01" ;;
    4) MT4_SERVER="Exness-Demo" ;;
    5) MT4_SERVER="XM.COM-Demo 3" ;;
    6) MT4_SERVER="FBS-Demo" ;;
    7) MT4_SERVER="Alpari-Demo" ;;
    8) MT4_SERVER="RoboForex-Demo" ;;
    9) read -p "Enter custom server: " MT4_SERVER ;;
    *) echo "Invalid choice"; exit 1 ;;
esac

echo ""
echo "Selected server: $MT4_SERVER"
echo ""

# Get account credentials
read -p "Enter demo account number: " MT4_LOGIN
read -sp "Enter demo password: " MT4_PASSWORD
echo ""

# Create or update .env file
echo ""
echo "Updating .env file..."

if [ -f .env ]; then
    # Backup existing .env
    cp .env .env.backup
    echo "Backed up existing .env to .env.backup"
fi

# Write new credentials
cat > .env << EOF
# MT4 Account Configuration
MT4_LOGIN=$MT4_LOGIN
MT4_PASSWORD=$MT4_PASSWORD
MT4_SERVER=$MT4_SERVER
EOF

echo "✓ .env file updated"
echo ""

# Restart container
read -p "Restart container now? (y/n): " restart_choice

if [[ $restart_choice =~ ^[Yy]$ ]]; then
    echo "Restarting container..."
    docker-compose down
    docker-compose up -d
    
    echo "Waiting for services to start..."
    sleep 10
    
    # Run diagnostic
    if [ -f ./master_diagnostic.sh ]; then
        echo ""
        echo "Running diagnostic..."
        ./master_diagnostic.sh
    fi
else
    echo "To apply changes, run:"
    echo "  docker-compose down"
    echo "  docker-compose up -d"
fi

echo ""
echo "Demo account setup complete!"
echo ""
echo "Tips:"
echo "1. Make sure you have registered for a demo account with your chosen broker"
echo "2. Server names are case-sensitive"
echo "3. Some brokers require you to open a demo account through their website first"
echo "4. If connection fails, try connecting with the same credentials in regular MT4 first"
