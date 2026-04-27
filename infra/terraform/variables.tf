variable "aws_region" {
  description = "AWS region for ECS, ECR, ALB, logs, and Lightsail."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project/application name used in AWS resource names."
  type        = string
  default     = "squinia"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "prod"
}

variable "container_port" {
  description = "Port exposed by the FastAPI container."
  type        = number
  default     = 8000
}

variable "ecs_desired_count" {
  description = "Desired ECS task count. Use 0 for the first bootstrap apply before the first image exists, then CI raises it to 1."
  type        = number
  default     = 1
}

variable "ecs_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "ecs_memory" {
  description = "Fargate task memory MiB."
  type        = number
  default     = 1024
}

variable "container_image_tag" {
  description = "Initial image tag for the Terraform-managed task definition. CI replaces task definition revisions with immutable SHA tags."
  type        = string
  default     = "bootstrap"
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. When set, ALB serves HTTPS on 443 and redirects HTTP to HTTPS."
  type        = string
  default     = ""
}

variable "frontend_origin" {
  description = "Production frontend origin used for CORS and app links."
  type        = string
  default     = "https://app.squinia.com"
}

variable "cors_origins_json" {
  description = "JSON array string for Pydantic CORS_ORIGINS, for example [\"https://app.squinia.com\"]."
  type        = string
  default     = "[\"https://app.squinia.com\"]"
}

variable "app_name" {
  description = "FastAPI APP_NAME."
  type        = string
  default     = "Squinia API"
}

variable "log_level" {
  description = "Application log level."
  type        = string
  default     = "INFO"
}

variable "email_provider" {
  description = "ses, console, or none."
  type        = string
  default     = "none"
}

variable "ses_from_email" {
  description = "SES sender address when EMAIL_PROVIDER=ses."
  type        = string
  default     = "noreply@squinia.com"
}

variable "livekit_url" {
  description = "LiveKit Cloud websocket URL, for example wss://your-project.livekit.cloud."
  type        = string
  default     = ""
}

variable "livekit_agent_name" {
  description = "LiveKit worker agent name."
  type        = string
  default     = "squinia-voice-agent"
}

variable "livekit_worker_autostart" {
  description = "Start the integrated LiveKit worker subprocess inside the backend task."
  type        = bool
  default     = true
}

variable "openrouter_chat_model" {
  description = "OpenRouter chat model for text simulations."
  type        = string
  default     = "openai/gpt-4o-mini"
}

variable "openrouter_guard_model" {
  description = "OpenRouter moderation/guard model."
  type        = string
  default     = "meta-llama/llama-guard-3-8b"
}

variable "openai_chat_model" {
  description = "OpenAI fallback chat model."
  type        = string
  default     = "gpt-4o-mini"
}

variable "db_name" {
  description = "Lightsail PostgreSQL database name."
  type        = string
  default     = "squinia"
}

variable "db_master_username" {
  description = "Lightsail PostgreSQL master username."
  type        = string
  default     = "squinia_admin"
}

variable "db_master_password" {
  description = "Lightsail PostgreSQL master password. Stored in Terraform state by the AWS provider; keep state private."
  type        = string
  sensitive   = true
}

variable "lightsail_db_blueprint_id" {
  description = "Lightsail database engine blueprint."
  type        = string
  default     = "postgres_16"
}

variable "lightsail_db_bundle_id" {
  description = "Lightsail database size. micro_2_0 is the cheapest production-sane starting point."
  type        = string
  default     = "micro_2_0"
}

variable "secret_names" {
  description = "Environment variable names stored in Secrets Manager and injected into ECS."
  type        = set(string)
  default = [
    "SECRET_KEY",
    "INTERNAL_API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "OPENAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "OPENROUTER_API_KEY",
    "CARTESIA_API_KEY",
    "GROQ_API_KEY"
  ]
}

variable "github_repository" {
  description = "Optional GitHub repository allowed to deploy with OIDC, in owner/repo form."
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "Branch allowed to assume the GitHub Actions deploy role."
  type        = string
  default     = "main"
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub OIDC provider ARN. Leave empty to create one when github_repository is set."
  type        = string
  default     = ""
}
