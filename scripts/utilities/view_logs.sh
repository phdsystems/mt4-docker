#!/bin/bash

CONTAINER="mt4-docker"

echo "MT4 Docker Logs"
echo "==============="
echo ""
echo "1. Container logs"
echo "2. MT4 logs"
echo "3. EA activity"
echo "4. All logs"
echo ""
read -p "Select (1-4): " option

case $option in
    1) docker logs -f $CONTAINER ;;
    2) docker exec $CONTAINER tail -f /mt4/logs/mt4.log ;;
    3) docker exec $CONTAINER tail -f /mt4/MQL4/Files/ea_activity.log ;;
    4) docker exec $CONTAINER tail -f /mt4/logs/*.log ;;
    *) echo "Invalid" ;;
esac
