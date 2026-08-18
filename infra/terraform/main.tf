/*
Root Module — Healthcare Data Platform Infrastructure
Orchestrates: VPC → EKS (+ IRSA) → ECR → S3 Data Lake → Snowflake objects.

Usage:
  cd infra/terraform/environments/dev
  terraform init
  terraform plan  -var-file=terraform.tfvars
  terraform apply -var-file=terraform.tfvars

See BOOTSTRAP.md before the very first apply (remote state setup).
*/

module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

module "eks" {
  source = "./modules/eks"

  project_name         = var.project_name
  environment          = var.environment
  cluster_version      = var.eks_cluster_version
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  public_subnet_ids    = module.vpc.public_subnet_ids
  node_instance_types  = var.eks_node_instance_types
  node_min_size        = var.eks_node_min_size
  node_max_size        = var.eks_node_max_size
  node_desired_size    = var.eks_node_desired_size
}

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

module "s3" {
  source = "./modules/s3"

  bucket_name  = var.datalake_bucket_name
  project_name = var.project_name
  environment  = var.environment
}

module "snowflake" {
  source = "./modules/snowflake"

  environment    = var.environment
  warehouse_size = var.snowflake_warehouse_size
}

# ─── Kubernetes namespace + secrets (bridges Terraform-provisioned infra to k8s) ─
resource "kubernetes_namespace" "healthcare" {
  metadata {
    name = "healthcare"
    labels = {
      environment = var.environment
    }
  }
  depends_on = [module.eks]
}

resource "kubernetes_service_account" "api" {
  metadata {
    name      = "api-service-account"
    namespace = kubernetes_namespace.healthcare.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = module.eks.api_service_account_role_arn
    }
  }
}

# Secrets are created here (values from CI/CD-injected variables) so app pods
# reference a stable k8s Secret name regardless of where the value originates.
resource "kubernetes_secret" "app_secrets" {
  metadata {
    name      = "healthcare-app-secrets"
    namespace = kubernetes_namespace.healthcare.metadata[0].name
  }
  data = {
    OPENAI_API_KEY      = var.openai_api_key
    SNOWFLAKE_ACCOUNT   = var.snowflake_account
    SNOWFLAKE_PASSWORD  = var.snowflake_password
    SNOWFLAKE_WAREHOUSE = module.snowflake.warehouse_name
    SNOWFLAKE_DATABASE  = module.snowflake.database_name
  }
  type = "Opaque"
}
