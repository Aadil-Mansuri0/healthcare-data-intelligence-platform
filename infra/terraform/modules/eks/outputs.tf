output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "cluster_certificate_authority_data" {
  value = aws_eks_cluster.this.certificate_authority[0].data
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.eks.arn
}

output "api_service_account_role_arn" {
  description = "Annotate the k8s ServiceAccount with this ARN to enable IRSA"
  value       = aws_iam_role.api_service_account.arn
}
