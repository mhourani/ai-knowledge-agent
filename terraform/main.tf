# ============================================================================
# AI Knowledge Agent — AWS Infrastructure
#
# This Terraform configuration provisions the complete AWS
# infrastructure needed to run the AI Knowledge Agent on EKS:
#
#   - VPC with public and private subnets
#   - EKS cluster with managed node groups
#   - ECR repository for container images
#   - IAM roles with least-privilege policies
#   - Secrets Manager for API keys
#   - ALB Ingress Controller for external access
#
# Usage:
#   terraform init
#   terraform plan -var="anthropic_api_key=sk-ant-xxxxx"
#   terraform apply -var="anthropic_api_key=sk-ant-xxxxx"
#
# After apply, configure kubectl:
#   aws eks update-kubeconfig --name <cluster_name> --region <region>
#
# Then deploy the application with Helm:
#   helm install my-agent ../chart -f values-aws.yaml
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for remote state (recommended for team environments)
  # backend "s3" {
  #   bucket         = "my-terraform-state"
  #   key            = "ai-knowledge-agent/terraform.tfstate"
  #   region         = "us-west-2"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Project     = var.project_name
        Environment = var.environment
        ManagedBy   = "terraform"
      },
      var.tags
    )
  }
}

# Data sources for the current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values used across multiple files
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
}
