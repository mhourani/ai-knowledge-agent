# ============================================================================
# ECR — Elastic Container Registry
#
# Stores the Docker image for the AI Knowledge Agent.
# CI/CD pipeline builds the image and pushes it here.
# EKS worker nodes pull from here using the ecr:ReadOnly IAM policy.
#
# Image lifecycle policy automatically cleans up old untagged images
# to control storage costs.
# ============================================================================

resource "aws_ecr_repository" "agent" {
  name                 = "${local.name_prefix}/agent"
  image_tag_mutability = "MUTABLE"  # Allow tag overwriting (e.g., :latest)

  # Scan images for vulnerabilities on push
  image_scanning_configuration {
    scan_on_push = true
  }

  # Encrypt images at rest with AWS-managed KMS key
  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${local.name_prefix}-agent"
  }
}

# Clean up untagged images after 30 days to control costs
resource "aws_ecr_lifecycle_policy" "agent" {
  repository = aws_ecr_repository.agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Remove untagged images after 30 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only the last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
