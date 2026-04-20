# ============================================================================
# IAM Roles and Policies
#
# EKS requires two IAM roles:
#   1. Cluster role — used by the EKS control plane
#   2. Node role — used by the EC2 worker nodes
#
# Both follow least-privilege principles, using only the
# AWS-managed policies that EKS requires.
# ============================================================================

# ---------- EKS Cluster Role ----------
# The control plane uses this role to manage AWS resources
# (ENIs, security groups, logs) on your behalf.

resource "aws_iam_role" "eks_cluster" {
  name = "${local.name_prefix}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}

# ---------- EKS Node Role ----------
# Worker nodes use this role to join the cluster, pull images
# from ECR, and write logs to CloudWatch.

resource "aws_iam_role" "eks_nodes" {
  name = "${local.name_prefix}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

# ---------- Secrets Manager Access ----------
# Allows pods to read API keys from Secrets Manager via
# the CSI Secrets Store Driver or application-level SDK calls.

resource "aws_iam_policy" "secrets_access" {
  name        = "${local.name_prefix}-secrets-access"
  description = "Allow EKS pods to read secrets from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.api_keys.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "nodes_secrets_access" {
  policy_arn = aws_iam_policy.secrets_access.arn
  role       = aws_iam_role.eks_nodes.name
}
