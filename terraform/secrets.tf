# ============================================================================
# Secrets Manager
#
# Stores API keys encrypted at rest with AWS KMS. This is the
# production-grade alternative to storing secrets in Helm values
# or Kubernetes Secrets (which are only base64-encoded, not encrypted).
#
# In production, use the External Secrets Operator or the CSI
# Secrets Store Driver to sync these secrets into Kubernetes pods
# automatically. The IAM policy in iam.tf grants the node role
# permission to read this specific secret.
# ============================================================================

resource "aws_secretsmanager_secret" "api_keys" {
  name        = "${local.name_prefix}/api-keys"
  description = "API keys for the AI Knowledge Agent (Anthropic, OpenAI)"

  # Disable recovery window in dev to allow clean terraform destroy
  # In production, keep the default 30-day recovery window
  recovery_window_in_days = var.environment == "dev" ? 0 : 30

  tags = {
    Name = "${local.name_prefix}-api-keys"
  }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id

  secret_string = jsonencode({
    ANTHROPIC_API_KEY  = var.anthropic_api_key
    OPENAI_API_KEY     = var.openai_api_key
  })
}
