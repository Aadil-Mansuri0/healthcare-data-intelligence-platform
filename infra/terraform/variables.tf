variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment: dev | staging | prod"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Short project identifier used in resource naming"
  type        = string
  default     = "healthcare-platform"
}

# ─── VPC ──────────────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "AZs to spread subnets across (min 2 for EKS HA control plane)"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

# ─── EKS ──────────────────────────────────────────────────────────────────────
variable "eks_cluster_version" {
  description = "Kubernetes version for the EKS control plane"
  type        = string
  default     = "1.29"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for the managed node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "eks_node_min_size" {
  type    = number
  default = 2
}

variable "eks_node_max_size" {
  type    = number
  default = 6
}

variable "eks_node_desired_size" {
  type    = number
  default = 2
}

# ─── S3 ───────────────────────────────────────────────────────────────────────
variable "datalake_bucket_name" {
  description = "S3 bucket name for the Medallion data lake (must be globally unique)"
  type        = string
  default     = "healthcare-datalake"
}

# ─── Snowflake ──────────────────────────────────────────────────────────────────
variable "snowflake_warehouse_size" {
  description = "Snowflake virtual warehouse size"
  type        = string
  default     = "XSMALL"
}

# ─── Secrets (values injected via CI/CD secret store, never committed) ────────
variable "openai_api_key" {
  description = "OpenAI API key — sourced from GitHub Actions secrets / AWS Secrets Manager"
  type        = string
  sensitive   = true
  default     = ""
}

variable "snowflake_account" {
  type      = string
  sensitive = true
  default   = ""
}

variable "snowflake_password" {
  type      = string
  sensitive = true
  default   = ""
}
