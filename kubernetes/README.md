# Kubernetes Deployment for MT4 Docker ZeroMQ

This directory contains Kubernetes manifests and Helm charts for deploying the MT4 trading system with ZeroMQ, WebSocket, and REST API support.

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3.x (for Helm deployment)
- Ingress controller (nginx-ingress recommended)
- cert-manager (for automatic TLS certificates)
- Persistent volume provisioner

## Directory Structure

```
kubernetes/
├── namespace.yaml              # Namespace definition
├── configmap.yaml             # Configuration maps
├── secrets.yaml               # Secret definitions
├── persistent-volumes.yaml     # PVC definitions
├── mt4-deployment.yaml        # MT4 terminal deployment
├── api-deployment.yaml        # REST API deployment
├── websocket-deployment.yaml  # WebSocket server deployment
├── redis-deployment.yaml      # Redis cache deployment
├── monitoring-deployment.yaml # Prometheus & Grafana
├── ingress.yaml              # Ingress rules
├── network-policies.yaml     # Network security policies
├── jobs.yaml                 # Batch jobs and CronJobs
├── kustomization.yaml        # Kustomize configuration
├── overlays/                 # Environment-specific configs
│   └── development/
└── helm/                     # Helm chart
    ├── Chart.yaml
    └── values.yaml
```

## Quick Start

### Using kubectl

1. Create namespace:
```bash
kubectl create namespace mt4-trading
```

2. Create secrets (edit first):
```bash
kubectl apply -f secrets.yaml
```

3. Deploy all resources:
```bash
kubectl apply -f .
```

### Using Kustomize

Deploy with kustomize:
```bash
kubectl apply -k .
```

For development environment:
```bash
kubectl apply -k overlays/development/
```

### Using Helm

1. Install the chart:
```bash
helm install mt4-trading ./helm \
  --namespace mt4-trading \
  --create-namespace \
  --values helm/values.yaml
```

2. Upgrade:
```bash
helm upgrade mt4-trading ./helm \
  --namespace mt4-trading \
  --values helm/values.yaml
```

## Configuration

### Environment Variables

Key environment variables to configure:

```yaml
MT4_SERVER: "your.broker.server:443"
MT4_LOGIN: "your_account"
MT4_PASSWORD: "your_password"
JWT_SECRET: "your-secret-key"
ADMIN_TOKEN: "admin-token"
```

### Persistent Storage

Configure storage classes based on your cloud provider:

- **AWS**: Use `gp3` for fast SSD storage
- **GCP**: Use `pd-ssd` for SSD persistent disks
- **Azure**: Use `Premium_LRS` for premium storage

### Ingress Configuration

Update ingress hosts in `ingress.yaml`:

```yaml
spec:
  rules:
  - host: api.your-domain.com
  - host: ws.your-domain.com
  - host: monitor.your-domain.com
```

### Resource Limits

Adjust resource requests and limits based on your needs:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Security

### Network Policies

Network policies are enforced by default. Key policies:

- MT4 terminal only accepts connections from API/WebSocket pods
- Redis only accepts connections from API pods
- Default deny all traffic policy

### Pod Security

- All pods run as non-root users
- Security contexts are enforced
- Read-only root filesystems where possible

### Secrets Management

Consider using:
- Kubernetes Secrets with encryption at rest
- External secret management (Vault, AWS Secrets Manager)
- Sealed Secrets for GitOps

## Monitoring

### Prometheus Metrics

Available metrics endpoints:
- API: `http://mt4-api-service:5000/metrics`
- WebSocket: `http://mt4-websocket-service:8765/metrics`

### Grafana Dashboards

Access Grafana:
```bash
kubectl port-forward -n mt4-trading svc/grafana-service 3000:3000
```

Default credentials: `admin` / `<password from secret>`

### Logging

View logs:
```bash
# MT4 terminal logs
kubectl logs -n mt4-trading deployment/mt4-terminal

# API logs
kubectl logs -n mt4-trading deployment/mt4-api

# All pods
kubectl logs -n mt4-trading -l app.kubernetes.io/part-of=mt4-trading-system
```

## Scaling

### Horizontal Pod Autoscaling

API service autoscales based on CPU/memory:
```bash
kubectl get hpa -n mt4-trading
```

### Manual Scaling

Scale deployments:
```bash
# Scale API
kubectl scale deployment mt4-api --replicas=5 -n mt4-trading

# Scale WebSocket
kubectl scale deployment mt4-websocket --replicas=3 -n mt4-trading
```

## Backup and Recovery

### Automated Backups

CronJob runs daily backups at 2 AM UTC:
```bash
kubectl get cronjobs -n mt4-trading
```

### Manual Backup

Trigger manual backup:
```bash
kubectl create job --from=cronjob/mt4-backup mt4-backup-manual -n mt4-trading
```

### Restore from Backup

1. Stop MT4 deployment:
```bash
kubectl scale deployment mt4-terminal --replicas=0 -n mt4-trading
```

2. Restore data:
```bash
kubectl exec -it <backup-pod> -- tar -xzf backup.tar.gz -C /mt4
```

3. Start MT4:
```bash
kubectl scale deployment mt4-terminal --replicas=1 -n mt4-trading
```

## Troubleshooting

### Common Issues

1. **MT4 not starting**
   - Check VNC password in environment
   - Verify broker credentials
   - Check persistent volume permissions

2. **WebSocket connection failures**
   - Verify ingress annotations for WebSocket support
   - Check network policies
   - Ensure sticky sessions are enabled

3. **High memory usage**
   - Review resource limits
   - Check for memory leaks in logs
   - Enable memory profiling

### Debug Commands

```bash
# Get events
kubectl get events -n mt4-trading --sort-by='.lastTimestamp'

# Describe pod
kubectl describe pod <pod-name> -n mt4-trading

# Execute shell in pod
kubectl exec -it <pod-name> -n mt4-trading -- /bin/bash

# Check network policies
kubectl get networkpolicy -n mt4-trading
```

## Production Checklist

- [ ] Update all secrets with production values
- [ ] Configure proper ingress hosts and TLS
- [ ] Set appropriate resource limits
- [ ] Enable monitoring and alerting
- [ ] Configure backup destination
- [ ] Review and apply network policies
- [ ] Enable pod security policies
- [ ] Set up external secret management
- [ ] Configure proper storage classes
- [ ] Test disaster recovery procedures

## Maintenance

### Rolling Updates

Update image:
```bash
kubectl set image deployment/mt4-api api=mt4-api:v2.0 -n mt4-trading
```

### Database Migrations

Run migrations:
```bash
kubectl apply -f jobs.yaml
```

### Cleanup

Remove old resources:
```bash
kubectl delete job -n mt4-trading --field-selector status.successful=1
```

## Support

For issues and questions:
- Check pod logs and events
- Review monitoring dashboards
- Consult disaster recovery guide
- Contact support team