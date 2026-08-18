output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}

output "datalake_bucket_name" {
  value = module.s3.datalake_bucket_name
}

output "snowflake_warehouse" {
  value = module.snowflake.warehouse_name
}

output "kubeconfig_update_command" {
  description = "Run this after apply to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}
