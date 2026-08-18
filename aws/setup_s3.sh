#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# AWS S3 Data Lake Setup — Healthcare Pipeline
# Creates buckets with Medallion-aligned prefixes, versioning, and lifecycle rules
# ═══════════════════════════════════════════════════════════════════════════
set -e

REGION="ap-south-1"
DATALAKE_BUCKET="healthcare-datalake"
SCRIPTS_BUCKET="healthcare-scripts"

echo "Creating S3 buckets in $REGION..."

aws s3api create-bucket \
  --bucket "$DATALAKE_BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

aws s3api create-bucket \
  --bucket "$SCRIPTS_BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

echo "Enabling versioning (protects against accidental overwrite/delete)..."
aws s3api put-bucket-versioning \
  --bucket "$DATALAKE_BUCKET" \
  --versioning-configuration Status=Enabled

echo "Applying server-side encryption (SSE-S3)..."
aws s3api put-bucket-encryption \
  --bucket "$DATALAKE_BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

echo "Blocking all public access..."
aws s3api put-public-access-block \
  --bucket "$DATALAKE_BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "Applying lifecycle policy (Bronze → Glacier after 90 days, expire after 2 years)..."
aws s3api put-bucket-lifecycle-configuration \
  --bucket "$DATALAKE_BUCKET" \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "BronzeArchival",
        "Filter": {"Prefix": "bronze/"},
        "Status": "Enabled",
        "Transitions": [
          {"Days": 90, "StorageClass": "GLACIER"}
        ],
        "Expiration": {"Days": 730}
      },
      {
        "ID": "SilverIntelligentTiering",
        "Filter": {"Prefix": "silver/"},
        "Status": "Enabled",
        "Transitions": [
          {"Days": 60, "StorageClass": "INTELLIGENT_TIERING"}
        ]
      }
    ]
  }'

echo "Creating folder structure (Medallion prefixes)..."
for prefix in bronze silver gold; do
  aws s3api put-object --bucket "$DATALAKE_BUCKET" --key "${prefix}/"
done

echo "✅ S3 data lake setup complete: $DATALAKE_BUCKET, $SCRIPTS_BUCKET"
