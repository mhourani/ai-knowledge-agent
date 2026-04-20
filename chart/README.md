# AI Knowledge Agent — Helm Chart

This Helm chart deploys the enterprise agentic RAG system on any
Kubernetes cluster (EKS, AKS, GKE, or self-hosted). It manages
two services:

1. **Agent** — the Streamlit + LangGraph application
2. **ChromaDB** — the vector store, running as a separate service
   with persistent storage

The chart follows the same architectural pattern as the
docker-compose stack — same code, same environment-based
configuration, different deployment target.

## Quick Start

```bash
# From the project root
helm install my-agent ./chart \
  --set secrets.anthropicApiKey=sk-ant-xxxxx

# With a custom values file
helm install my-agent ./chart -f my-values.yaml

# Access via port-forward
kubectl port-forward svc/my-agent-ai-knowledge-agent 8501:80
```

Then open http://localhost:8501.

## Configuration

All configuration is in `values.yaml`. Key settings:

| Parameter | Description | Default |
|---|---|---|
| `agent.replicaCount` | Number of agent replicas | `1` |
| `agent.image.repository` | Agent container image | `ai-knowledge-agent` |
| `agent.image.tag` | Image tag | `latest` |
| `agent.resources.requests.memory` | Memory request | `512Mi` |
| `agent.autoscaling.enabled` | Enable HPA | `false` |
| `chroma.enabled` | Deploy ChromaDB | `true` |
| `chroma.persistence.enabled` | Persist vector data | `true` |
| `chroma.persistence.size` | PVC size | `10Gi` |
| `chroma.persistence.storageClass` | Storage class | `""` (default) |
| `secrets.anthropicApiKey` | Anthropic API key | `""` |
| `ingress.enabled` | Create Ingress resource | `false` |
| `service.type` | Service type | `ClusterIP` |

## Cloud-Specific Deployment

### AWS EKS

```yaml
# values-aws.yaml
agent:
  image:
    repository: 123456789.dkr.ecr.us-west-2.amazonaws.com/ai-knowledge-agent
chroma:
  persistence:
    storageClass: gp3
ingress:
  enabled: true
  className: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
  hosts:
    - host: ai-agent.example.com
      paths:
        - path: /
          pathType: Prefix
```

### Azure AKS

```yaml
# values-azure.yaml
agent:
  image:
    repository: myregistry.azurecr.io/ai-knowledge-agent
chroma:
  persistence:
    storageClass: managed-premium
ingress:
  enabled: true
  className: azure/application-gateway
  hosts:
    - host: ai-agent.example.com
      paths:
        - path: /
          pathType: Prefix
```

## Secrets Management

The chart includes a basic Kubernetes Secret for API keys. **For
production deployments, replace this with:**

- **AWS:** External Secrets Operator + AWS Secrets Manager
- **Azure:** CSI Secrets Store Driver + Azure Key Vault
- **Any cloud:** HashiCorp Vault or Sealed Secrets

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Kubernetes Cluster              │
│                                                  │
│  ┌──────────────┐       ┌───────────────────┐   │
│  │   Ingress    │──────▶│   Agent Service   │   │
│  │  (optional)  │       │   (ClusterIP)     │   │
│  └──────────────┘       └───────┬───────────┘   │
│                                 │               │
│                        ┌────────▼────────┐      │
│                        │  Agent Pod(s)   │      │
│                        │  Streamlit +    │      │
│                        │  LangGraph      │      │
│                        └────────┬────────┘      │
│                                 │ HTTP           │
│                        ┌────────▼────────┐      │
│                        │  ChromaDB       │      │
│                        │  Service        │      │
│                        └────────┬────────┘      │
│                                 │               │
│                        ┌────────▼────────┐      │
│                        │  ChromaDB Pod   │      │
│                        │  + PVC          │      │
│                        └─────────────────┘      │
└─────────────────────────────────────────────────┘
```

## Upgrading

```bash
# Update image tag
helm upgrade my-agent ./chart --set agent.image.tag=v1.2.3

# Full upgrade with new values
helm upgrade my-agent ./chart -f my-values.yaml

# Rollback
helm rollback my-agent 1
```

## Production Considerations

This chart provides a working Kubernetes deployment. For
production, see [PRODUCTION.md](../PRODUCTION.md) for the full
readiness inventory, including observability, cost management,
security hardening, and multi-tenancy.
