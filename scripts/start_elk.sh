#!/bin/bash
# Start ELK Stack for MT4 Docker

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting ELK Stack for MT4 Docker...${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p logs/mt4 logs/bridge logs/security logs/market_data logs/zeromq
mkdir -p config/logstash/templates

# Create Elasticsearch template
cat > config/logstash/templates/mt4-logs.json << 'EOF'
{
  "index_patterns": ["mt4-logs-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.refresh_interval": "5s"
  },
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "level": { "type": "keyword" },
      "logger": { "type": "keyword" },
      "message": { "type": "text" },
      "event_type": { "type": "keyword" },
      "symbol": { "type": "keyword" },
      "bid": { "type": "float" },
      "ask": { "type": "float" },
      "spread": { "type": "float" },
      "volume": { "type": "long" },
      "tags": { "type": "keyword" },
      "error_type": { "type": "keyword" },
      "security_event": { "type": "keyword" },
      "metric": { "type": "keyword" },
      "value": { "type": "float" },
      "unit": { "type": "keyword" }
    }
  }
}
EOF

# Start ELK stack
echo -e "${YELLOW}Starting ELK services...${NC}"
docker-compose -f docker-compose.elk.yml up -d

# Wait for Elasticsearch to be ready
echo -e "${YELLOW}Waiting for Elasticsearch to be ready...${NC}"
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"yellow"\|"status":"green"'; do
    echo -n "."
    sleep 5
done
echo -e "\n${GREEN}Elasticsearch is ready!${NC}"

# Wait for Kibana to be ready
echo -e "${YELLOW}Waiting for Kibana to be ready...${NC}"
until curl -s http://localhost:5601/api/status | grep -q '"state":"green"'; do
    echo -n "."
    sleep 5
done
echo -e "\n${GREEN}Kibana is ready!${NC}"

# Create index patterns
echo -e "${YELLOW}Creating Kibana index patterns...${NC}"
curl -X POST "localhost:5601/api/saved_objects/index-pattern" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "title": "mt4-logs-*",
      "timeFieldName": "@timestamp"
    }
  }' 2>/dev/null || true

curl -X POST "localhost:5601/api/saved_objects/index-pattern" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "title": "mt4-metrics-*",
      "timeFieldName": "@timestamp"
    }
  }' 2>/dev/null || true

# Import dashboards if they exist
if [ -f "config/kibana/dashboards/mt4-dashboard.json" ]; then
    echo -e "${YELLOW}Importing Kibana dashboards...${NC}"
    curl -X POST "localhost:5601/api/saved_objects/_import" \
      -H "kbn-xsrf: true" \
      -F file=@config/kibana/dashboards/mt4-dashboard.json 2>/dev/null || true
fi

# Show status
echo -e "\n${GREEN}ELK Stack is running!${NC}"
echo -e "${YELLOW}Services:${NC}"
echo "  - Elasticsearch: http://localhost:9200"
echo "  - Kibana: http://localhost:5601"
echo "  - Logstash TCP: localhost:5000"
echo "  - Logstash Beats: localhost:5044"

# Show logs command
echo -e "\n${YELLOW}To view logs:${NC}"
echo "  docker-compose -f docker-compose.elk.yml logs -f"

# Show stop command
echo -e "\n${YELLOW}To stop ELK stack:${NC}"
echo "  docker-compose -f docker-compose.elk.yml down"

echo -e "\n${GREEN}Setup complete!${NC}"