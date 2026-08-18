terraform {
  required_version = ">= 1.7.0"

  # Remote state — S3 backend with DynamoDB locking (prevents concurrent
  # `terraform apply` races, which is the #1 cause of corrupted state in teams).
  # Bootstrap this bucket + table manually ONCE before first `terraform init`
  # (see infra/terraform/BOOTSTRAP.md) — you cannot use Terraform to create
  # its own remote backend on the very first run (chicken-and-egg problem).
  backend "s3" {
    bucket         = "healthcare-platform-tfstate"
    key            = "healthcare-platform/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "healthcare-platform-tf-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.2"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.87"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "healthcare-data-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Configured post-EKS-creation to talk to the cluster we just provisioned —
# this is the standard "two-phase apply" pattern for Terraform + EKS + Helm.
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.this.token
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    token                  = data.aws_eks_cluster_auth.this.token
  }
}

provider "snowflake" {
  # Auth via SNOWFLAKE_USER / SNOWFLAKE_PASSWORD / SNOWFLAKE_ACCOUNT env vars
  # (never hardcode credentials in .tf files — see environments/*/terraform.tfvars.example)
  role = "SYSADMIN"
}

data "aws_eks_cluster_auth" "this" {
  name = module.eks.cluster_name
}
