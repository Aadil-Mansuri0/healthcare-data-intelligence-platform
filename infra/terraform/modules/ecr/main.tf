variable "project_name" { type = string }
variable "environment" { type = string }

locals {
  repos = ["api", "frontend", "airflow"]
}

resource "aws_ecr_repository" "images" {
  for_each             = toset(local.repos)
  name                 = "${var.project_name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"  # prevents accidental "latest" overwrite drift

  image_scanning_configuration {
    scan_on_push = true  # automatic vulnerability scanning — MNC baseline requirement
  }
}

resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each   = aws_ecr_repository.images
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 14 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 14
      }
      action = { type = "expire" }
    }]
  })
}

output "repository_urls" {
  value = { for k, v in aws_ecr_repository.images : k => v.repository_url }
}
