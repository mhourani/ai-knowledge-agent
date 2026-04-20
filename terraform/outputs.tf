# ============================================================================
# Outputs
#
# Values displayed after terraform apply and available to other
# Terraform configurations via terraform_remote_state.
#
# These outputs provide everything needed to deploy the Helm chart:
#   - kubectl configuration command
#   - ECR repository URL for docker push
#   - Cluster details for CI/CD pipeline configuration
# ============================================================================

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_version" {
  description = "EKS Kubernetes version"
  value       = aws_eks_cluster.main.version
}

output "ecr_repository_url" {
  description = "ECR repository URL — use this in docker push and Helm values"
  value       = aws_ecr_repository.agent.repository_url
}

output "secrets_manager_arn" {
  description = "ARN of the Secrets Manager secret containing API keys"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs where EKS nodes run"
  value       = aws_subnet.private[*].id
}

output "configure_kubectl" {
  description = "Command to configure kubectl for this cluster"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${local.region}"
}

output "docker_push_commands" {
  description = "Commands to build and push the Docker image to ECR"
  value       = <<-EOT
    # Authenticate Docker with ECR
    aws ecr get-login-password --region ${local.region} | docker login --username AWS --password-stdin ${local.account_id}.dkr.ecr.${local.region}.amazonaws.com

    # Build and push
    docker build -t ${aws_ecr_repository.agent.repository_url}:latest .
    docker push ${aws_ecr_repository.agent.repository_url}:latest
  EOT
}

output "helm_install_command" {
  description = "Command to deploy the application with Helm"
  value       = <<-EOT
    helm install my-agent ./chart \
      --set agent.image.repository=${aws_ecr_repository.agent.repository_url} \
      --set agent.image.tag=latest \
      --set secrets.anthropicApiKey=<your-key>
  EOT
}
