output "aws_region" {
  value = var.aws_region
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecs_task_definition_family" {
  value = aws_ecs_task_definition.backend.family
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "backend_base_url" {
  value = var.certificate_arn == "" ? "http://${aws_lb.main.dns_name}" : "https://${aws_lb.main.dns_name}"
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.backend.name
}

output "lightsail_db_endpoint" {
  value = aws_lightsail_database.postgres.master_endpoint_address
}

output "lightsail_db_port" {
  value = aws_lightsail_database.postgres.master_endpoint_port
}

output "lightsail_db_name" {
  value = var.db_name
}

output "lightsail_db_username" {
  value = var.db_master_username
}

output "database_url_template" {
  value     = "postgresql+asyncpg://${var.db_master_username}:<PASSWORD>@${aws_lightsail_database.postgres.master_endpoint_address}:${aws_lightsail_database.postgres.master_endpoint_port}/${var.db_name}?ssl=require"
  sensitive = true
}

output "secret_names" {
  value = {
    for key, secret in aws_secretsmanager_secret.backend : key => secret.name
  }
}

output "github_actions_repository_secrets" {
  value = {
    AWS_REGION                 = var.aws_region
    ECR_REPOSITORY             = aws_ecr_repository.backend.name
    ECS_CLUSTER                = aws_ecs_cluster.main.name
    ECS_SERVICE                = aws_ecs_service.backend.name
    ECS_TASK_DEFINITION_FAMILY = aws_ecs_task_definition.backend.family
    ECS_CONTAINER_NAME         = "backend"
    AWS_ROLE_TO_ASSUME         = var.github_repository == "" ? "set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY instead, or set var.github_repository and re-apply" : aws_iam_role.github_actions_deploy[0].arn
  }
}

output "github_actions_role_arn" {
  value = var.github_repository == "" ? null : aws_iam_role.github_actions_deploy[0].arn
}
