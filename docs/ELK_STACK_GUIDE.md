# ELK Stack Implementation Guide

## Overview

This guide describes the centralized logging implementation using the ELK (Elasticsearch, Logstash, Kibana) stack for the MT4 Docker project. The implementation provides real-time log aggregation, analysis, and visualization.

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────┐     ┌─────────────────┐     ┌────────┐
│ MT4 Bridge  │────▶│ Filebeat │────▶│    Logstash     │────▶│ Elastic│
│   Logger    │     └──────────┘     │   (Processing)  │     │ search │
└─────────────┘                      └─────────────────┘     └────────┘
                                              │                    ▲
┌─────────────┐                              ▼                    │
│  Security   │────────────────────▶ TCP Port 5000               │
│   Logger    │                                                   │
└─────────────┘                                                   │
                                                                  ▼
┌─────────────┐     ┌────────────┐                          ┌────────┐
│  Metrics    │────▶│ Metricbeat │─────────────────────────▶│ Kibana │
│  Exporter   │     └────────────┘                          └────────┘
└─────────────┘
```

## 📦 Components

### 1. **Elasticsearch**
- Data storage and search engine
- Stores all logs and metrics
- Provides full-text search capabilities
- Scales horizontally for large deployments

### 2. **Logstash**
- Log processing pipeline
- Parses and enriches log data
- Routes logs to appropriate indices
- Filters and transforms data

### 3. **Kibana**
- Visualization and dashboards
- Real-time monitoring
- Log analysis and search
- Custom alerts and reports

### 4. **Filebeat**
- Lightweight log shipper
- Monitors log files
- Ships logs to Logstash
- Handles log rotation

### 5. **Metricbeat**
- System and service metrics
- Docker container monitoring
- Performance metrics
- Resource utilization

## 🚀 Quick Start

### 1. Start ELK Stack

```bash
# Start all ELK services
docker-compose -f docker-compose.elk.yml up -d

# Check status
docker-compose -f docker-compose.elk.yml ps

# View logs
docker-compose -f docker-compose.elk.yml logs -f
```

### 2. Access Kibana

Open http://localhost:5601 in your browser.

### 3. Configure Index Patterns

1. Go to Stack Management → Index Patterns
2. Create pattern: `mt4-logs-*`
3. Create pattern: `mt4-metrics-*`
4. Set `@timestamp` as time field

### 4. Import Dashboards

```bash
# Import pre-configured dashboards
curl -X POST "localhost:5601/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -F file=@config/kibana/dashboards/mt4-dashboard.json
```

## 🔧 Configuration

### Python Logging Integration

```python
from services.logging.elk_logger import LoggerFactory, ELKLogger

# Configure logger factory
LoggerFactory.configure(
    logstash_host='localhost',
    logstash_port=5000,
    console_output=True,
    level='INFO'
)

# Get logger
logger = LoggerFactory.get_elk_logger('MyComponent')

# Log structured data
logger.log_market_tick('EURUSD', 1.1000, 1.1001, 1000)
logger.log_security_event('login_attempt', {'user': 'trader1'})
logger.log_performance_metric('latency', 2.5, 'ms')
```

### Bridge with ELK

```python
from services.zeromq_bridge.zmq_bridge_elk import ELKMarketDataBridge

# Create bridge with ELK logging
config = {
    'elk': {
        'host': 'localhost',
        'port': 5000,
        'console': True
    }
}

bridge = ELKMarketDataBridge(publisher, data_source, config)
```

## 📊 Log Structure

### Market Data Logs

```json
{
  "@timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "MarketDataBridge",
  "event_type": "market_tick",
  "symbol": "EURUSD",
  "bid": 1.1000,
  "ask": 1.1001,
  "spread": 0.0001,
  "volume": 1000,
  "tags": ["market_data", "tick"]
}
```

### Security Logs

```json
{
  "@timestamp": "2024-01-15T10:30:45.123Z",
  "level": "WARNING",
  "logger": "SecurityLogger",
  "event_type": "security",
  "security_event": "unauthorized_access",
  "details": {
    "client_ip": "192.168.1.100",
    "reason": "invalid_key"
  },
  "tags": ["security", "audit"]
}
```

### Performance Metrics

```json
{
  "@timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "PerformanceLogger",
  "event_type": "performance",
  "metric": "publish_latency",
  "value": 0.5,
  "unit": "ms",
  "tags": ["performance", "metrics"]
}
```

## 🔍 Kibana Queries

### Common Searches

```
# All errors
level:ERROR

# Market ticks for EURUSD
event_type:market_tick AND symbol:EURUSD

# Security events
tags:security

# High latency events
event_type:performance AND value:>10

# Failed authentication
security_event:auth_failed
```

### Advanced Queries

```
# Ticks with high spread
event_type:market_tick AND spread:>0.0005

# Errors in last hour
level:ERROR AND @timestamp:[now-1h TO now]

# Group by symbol
event_type:market_tick | stats count by symbol
```

## 📈 Dashboards

### 1. **Market Data Dashboard**
- Real-time tick rate
- Spread analysis
- Price charts
- Volume metrics

### 2. **Security Dashboard**
- Authentication attempts
- Key operations
- Security events timeline
- Anomaly detection

### 3. **Performance Dashboard**
- Latency metrics
- Throughput graphs
- Error rates
- Resource utilization

### 4. **System Dashboard**
- Container metrics
- CPU/Memory usage
- Network I/O
- Disk usage

## 🚨 Alerting

### Create Alerts in Kibana

1. Go to Stack Management → Watcher
2. Create new watcher:

```json
{
  "trigger": {
    "schedule": {
      "interval": "1m"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["mt4-logs-*"],
        "body": {
          "query": {
            "bool": {
              "filter": [
                {"term": {"level": "ERROR"}},
                {"range": {"@timestamp": {"gte": "now-5m"}}}
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total": {
        "gte": 10
      }
    }
  },
  "actions": {
    "send_email": {
      "email": {
        "to": "alerts@example.com",
        "subject": "MT4 Error Alert",
        "body": "{{ctx.payload.hits.total}} errors in last 5 minutes"
      }
    }
  }
}
```

## 🔧 Troubleshooting

### Common Issues

1. **Logs not appearing**
   ```bash
   # Check Logstash
   docker logs mt4_logstash
   
   # Test connection
   telnet localhost 5000
   
   # Send test log
   echo '{"test": "message"}' | nc localhost 5000
   ```

2. **High memory usage**
   ```yaml
   # Adjust JVM heap in docker-compose.elk.yml
   environment:
     - "ES_JAVA_OPTS=-Xms256m -Xmx256m"
   ```

3. **Slow queries**
   ```bash
   # Check cluster health
   curl -X GET "localhost:9200/_cluster/health?pretty"
   
   # Check index stats
   curl -X GET "localhost:9200/mt4-logs-*/_stats?pretty"
   ```

## 🎯 Best Practices

### 1. **Log Levels**
- DEBUG: Detailed debugging information
- INFO: General informational messages
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical issues

### 2. **Structured Logging**
- Always use structured JSON format
- Include relevant context
- Use consistent field names
- Add appropriate tags

### 3. **Performance**
- Batch log sends when possible
- Use appropriate log levels
- Implement log sampling for high-volume data
- Regular index maintenance

### 4. **Security**
- Never log sensitive data (passwords, keys)
- Use field masking for PII
- Implement access controls
- Enable audit logging

## 📚 Index Management

### Index Lifecycle Management (ILM)

```json
PUT _ilm/policy/mt4-logs-policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "5GB",
            "max_age": "7d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

## 🔄 Backup and Recovery

### Snapshot Repository

```bash
# Create repository
curl -X PUT "localhost:9200/_snapshot/mt4_backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backup/elasticsearch"
  }
}'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/mt4_backup/snapshot_1?wait_for_completion=true"

# Restore snapshot
curl -X POST "localhost:9200/_snapshot/mt4_backup/snapshot_1/_restore"
```

## 🚀 Production Deployment

### 1. **Scaling**
- Use multiple Elasticsearch nodes
- Deploy Logstash behind load balancer
- Use persistent volumes
- Implement clustering

### 2. **Security**
- Enable X-Pack security
- Use SSL/TLS for all connections
- Implement role-based access
- Regular security audits

### 3. **Monitoring**
- Monitor cluster health
- Set up alerting
- Track performance metrics
- Regular maintenance

The ELK stack provides comprehensive logging and monitoring capabilities for the MT4 Docker project, enabling real-time insights and troubleshooting.