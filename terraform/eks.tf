# ============================================================================
# EKS Cluster and Managed Node Group
#
# Creates:
#   - EKS control plane in private subnets
#   - Managed node group with auto-scaling
#   - CloudWatch logging for audit and diagnostics
#
# After terraform apply, configure kubectl with:
#   aws eks update-kubeconfig --name <cluster_name> --region <region>
# ============================================================================

resource "aws_eks_cluster" "main" {
  name     = local.name_prefix
  version  = var.kubernetes_version
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    # Control plane is accessible from within the VPC
    # Worker nodes connect from private subnets
    subnet_ids              = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true  # Set to false for production + VPN
  }

  # Enable control plane logging for audit and troubleshooting
  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
  ]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]

  tags = {
    Name = local.name_prefix
  }
}

# ---------- Managed Node Group ----------
# AWS manages the EC2 instances, AMI updates, and draining.
# Nodes run in private subnets — no direct internet access.

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name_prefix}-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.node_instance_types

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  # Allow node group to gracefully drain during updates
  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.ecr_read_only,
  ]

  tags = {
    Name = "${local.name_prefix}-nodes"
  }
}
