#!/bin/bash

echo "MT4 Demo Account Setup Helper"
echo "============================"
echo ""

# Popular demo servers
echo "Popular MT4 Demo Servers:"
echo "1. MetaQuotes-Demo"
echo "2. ICMarkets-Demo02"
echo "3. Pepperstone-Demo01"
echo "4. XM.COM-Demo 3"
echo "5. Exness-Demo"
echo "6. IG"
echo "7. Custom server"
echo ""

read -p "Select server (1-6): " choice

case $choice in
    1) MT4_SERVER="MetaQuotes-Demo" ;;
    2) MT4_SERVER="ICMarkets-Demo02" ;;
    3) MT4_SERVER="Pepperstone-Demo01" ;;
    4) MT4_SERVER="XM.COM-Demo 3" ;;
    5) MT4_SERVER="Exness-Demo" ;;
    6) MT4_SERVER="IG-LIVE" ;;    
    7) read -p "Enter server: " MT4_SERVER ;;
    *) echo "Invalid"; exit 1 ;;
esac

read -p "Enter demo account number: " MT4_LOGIN
read -sp "Enter demo password: " MT4_PASSWORD
echo ""

# Update .env
cat > .env << ENVFILE
# MT4 Account Configuration
MT4_LOGIN=$MT4_LOGIN
MT4_PASSWORD=$MT4_PASSWORD
MT4_SERVER=$MT4_SERVER

# EA Configuration
EA_NAME=AutoDeploy_EA
EA_SYMBOL=EURUSD
EA_TIMEFRAME=H1
ENVFILE

echo "Updated .env file"
echo ""

read -p "Restart container? (y/n): " restart
if [[ $restart =~ ^[Yy]$ ]]; then
    docker-compose down
    docker-compose up -d
    sleep 10
    ./scripts/troubleshooting/master_diagnostic.sh
fi

echo "Setup complete!"
