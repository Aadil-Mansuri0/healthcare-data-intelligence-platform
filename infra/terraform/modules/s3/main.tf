variable "bucket_name" { type = string }
variable "project_name" { type = string }
variable "environment" { type = string }

# ─── Data Lake Bucket ─────────────────────────────────────────────────────────
resource "aws_s3_bucket" "datalake" {
  bucket = "${var.bucket_name}-${var.environment}"
}

resource "aws_s3_bucket_versioning" "datalake" {
  bucket = aws_s3_bucket.datalake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "datalake" {
  bucket                  = aws_s3_bucket.datalake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  rule {
    id     = "bronze-archival"
    status = "Enabled"
    filter { prefix = "bronze/" }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration {
      days = 730
    }
  }

  rule {
    id     = "silver-intelligent-tiering"
    status = "Enabled"
    filter { prefix = "silver/" }

    transition {
      days          = 60
      storage_class = "INTELLIGENT_TIERING"
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ─── Scripts Bucket (Spark job artifacts) ──────────────────────────────────────
resource "aws_s3_bucket" "scripts" {
  bucket = "${var.project_name}-scripts-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "scripts" {
  bucket                  = aws_s3_bucket.scripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── Terraform State Bucket Note ────────────────────────────────────────────────
# The tfstate bucket itself (healthcare-platform-tfstate) is intentionally NOT
# managed here — see infra/terraform/BOOTSTRAP.md for why (chicken-and-egg:
# Terraform can't create the backend it depends on for its own state).
