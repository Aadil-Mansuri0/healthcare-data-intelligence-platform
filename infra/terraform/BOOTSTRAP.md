# Terraform Bootstrap — Remote State Setup

Terraform needs an S3 bucket + DynamoDB table for remote state *before* you can
run `terraform init` against `providers.tf` (which references that backend).
This is a one-time, manual step per AWS account — you cannot use Terraform
itself to create the backend it depends on (chicken-and-egg problem).

## Run once, manually, before the first `terraform init`:

```bash
# 1. State bucket
aws s3api create-bucket \
  --bucket healthcare-platform-tfstate \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

aws s3api put-bucket-versioning \
  --bucket healthcare-platform-tfstate \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket healthcare-platform-tfstate \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

aws s3api put-public-access-block \
  --bucket healthcare-platform-tfstate \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# 2. Lock table (prevents two people running `apply` at once and corrupting state)
aws dynamodb create-table \
  --table-name healthcare-platform-tf-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

## Then, per environment:

```bash
cd infra/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with real (non-secret) values

export TF_VAR_openai_api_key="sk-..."
export TF_VAR_snowflake_account="xy12345.ap-south-1"
export TF_VAR_snowflake_password="..."
# Never commit these — pass secrets via env vars or CI/CD secret store only.

terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## After apply:

```bash
# Configure kubectl to talk to the new EKS cluster
$(terraform output -raw kubeconfig_update_command)

# Verify
kubectl get nodes
kubectl get ns
```

## Destroy (careful — this is real infra with real cost):

```bash
terraform destroy -var-file=terraform.tfvars
```
