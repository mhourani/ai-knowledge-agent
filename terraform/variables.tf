# ============================================================================
# AI Knowledge Agent — AWS Infrastructure Variables
#
# These variables parameterize the entire deployment. Override them
# in a terraform.tfvars file or via -var flags.
# ============================================================================

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "ai-knowledge-agent"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

# ---------- Networking ----------

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs for high availability (minimum 2 for EKS)"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

# ---------- EKS ----------

variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 4
}

# ---------- Secrets ----------

variable "anthropic_api_key" {
  description = "Anthropic API key (stored in AWS Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key (optional, stored in AWS Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

# ---------- Tags ----------

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
