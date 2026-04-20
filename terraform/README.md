# AI Knowledge Agent — AWS Infrastructure (Terraform)

This Terraform configuration provisions the complete AWS infrastructure
needed to deploy the AI Knowledge Agent on Amazon EKS.

## What It Creates

| Resource | Purpose |
|---|---|
| **VPC** | Isolated network with public and private subnets across 2 AZs |
| **Internet Gateway** | Internet access for public subnets (ALB) |
| **NAT Gateway** | Outbound internet for private subnets (image pulls, API calls) |
| **EKS Cluster** | Managed Kubernetes control plane |
| **EKS Node Group** | Auto-scaling worker nodes in private subnets |
| **ECR Repository** | Container registry for the agent Docker image |
| **IAM Roles** | Least-privilege roles for the cluster and nodes |
| **Secrets Manager** | Encrypted storage for API keys (Anthropic, OpenAI) |

## Architecture

```
                    Internet
                       │
                ┌──────┴──────┐
                │   Internet  │
                │   Gateway   │
                └──────┬──────┘
                       │
          ┌────────────┴────────────┐
          │       Public Subnets     │
          │   ┌──────────────────┐  │
          │   │   ALB (Ingress)  │  │
          │   └────────┬─────────┘  │
          └────────────┼────────────┘
                       │
          ┌────────────┴────────────┐
          │      Private Subnets     │
          │                          │
          │   ┌──────────────────┐  │
          │   │  EKS Worker Nodes │  │
          │   │  ┌─────┐ ┌─────┐ │  │
          │   │  │Agent│ │Chroma│ │  │
          │   │  └─────┘ └─────┘ │  │
          │   └──────────────────┘  │
          │                          │
          │   ┌──────────────────┐  │
          │   │   NAT Gateway    │──┼──▶ LLM APIs, ECR
          │   └──────────────────┘  │
          └─────────────────────────┘
```

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0
- kubectl
- Helm 3

## Quick Start

```bash
cd terraform/aws

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var="anthropic_api_key=sk-ant-xxxxx"

# Apply
terraform apply -var="anthropic_api_key=sk-ant-xxxxx"

# Configure kubectl
$(terraform output -raw configure_kubectl)

# Verify cluster access
kubectl get nodes

# Deploy with Helm
helm install my-agent ../../chart \
  --set agent.image.repository=$(terraform output -raw ecr_repository_url) \
  --set secrets.anthropicApiKey=sk-ant-xxxxx
```

## Configuration

Create a `terraform.tfvars` file (NOT committed to git):

```hcl
project_name      = "ai-knowledge-agent"
environment       = "dev"
aws_region        = "us-west-2"
anthropic_api_key = "sk-ant-xxxxx"

# Scale up for production
node_instance_types = ["t3.large"]
node_desired_size   = 3
node_min_size       = 2
node_max_size       = 6
```

## Cost Estimates (dev environment)

| Resource | Approximate Monthly Cost |
|---|---|
| EKS Control Plane | $73 |
| 2x t3.medium nodes | $60 |
| NAT Gateway | $32 + data transfer |
| ECR | ~$1 (storage) |
| Secrets Manager | ~$1 |
| **Total (dev)** | **~$170/month** |

Production costs scale with node count, instance size, and data transfer.

## Security Notes

- Worker nodes run in **private subnets** with no direct internet access
- API keys are stored in **Secrets Manager** (encrypted with KMS), not in
  Kubernetes Secrets or environment variables
- ECR images are **scanned for vulnerabilities** on push
- IAM roles follow **least-privilege** — nodes can only read the
  specific secret they need
- EKS control plane logging is enabled for **API, audit, and authenticator**
- For production: set `endpoint_public_access = false` and use a VPN
  or bastion host for kubectl access

## Cleanup

```bash
# Remove all Helm releases first
helm uninstall my-agent

# Destroy all AWS resources
terraform destroy -var="anthropic_api_key=sk-ant-xxxxx"
```

## Next Steps

For the Azure equivalent, see `terraform/azure/`.
For CI/CD pipeline configuration, see `.github/workflows/`.
For production readiness inventory, see `PRODUCTION.md`.
