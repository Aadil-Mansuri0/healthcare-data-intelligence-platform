# AWS EC2 Deployment Guide

## Recommended Setup (Production)

| Component | Instance Type | Notes |
|---|---|---|
| Airflow (Webserver + Scheduler) | `t3.large` (2 vCPU, 8GB) | Or use MWAA (managed Airflow) instead |
| Spark Jobs | EMR cluster (transient, auto-terminate) | Don't run Spark on the Airflow box |
| FastAPI | `t3.medium` behind ALB, Auto Scaling Group (min 2) | Stateless — scales horizontally |
| Next.js Frontend | Vercel (recommended) or `t3.small` + Nginx | Or serve via S3+CloudFront as static export |

## Step 1: Launch EC2 Instance

```bash
aws ec2 run-instances \
  --image-id ami-0f5ee92e2d63afc18 \
  --instance-type t3.large \
  --key-name healthcare-key \
  --security-group-ids sg-xxxxxxxx \
  --subnet-id subnet-xxxxxxxx \
  --iam-instance-profile Name=healthcare-pipeline-role \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=healthcare-airflow}]' \
  --user-data file://ec2_bootstrap.sh
```

## Step 2: Security Group Rules

| Port | Source | Purpose |
|---|---|---|
| 22 | Your IP only | SSH |
| 8080 | ALB / VPN only | Airflow UI (never expose publicly) |
| 8000 | ALB | FastAPI |
| 443 | 0.0.0.0/0 | HTTPS (via ALB + ACM cert) |

## Step 3: Bootstrap Script (`ec2_bootstrap.sh`)

```bash
#!/bin/bash
yum update -y
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

git clone https://github.com/<your-org>/healthcare_advanced.git /opt/healthcare
cd /opt/healthcare/docker
docker-compose up -d
```

## Step 4: IAM Instance Profile
Attach the role created from `aws/iam_policy.json` — grants S3, CloudWatch Logs,
and Secrets Manager access without hardcoding AWS keys on the instance.

## Step 5: Use AWS Secrets Manager (not `.env` in production)
```bash
aws secretsmanager create-secret \
  --name healthcare/snowflake-creds \
  --secret-string '{"user":"...", "password":"..."}'
```
Fetch at container startup instead of baking secrets into images.

## Step 6: Auto Scaling for FastAPI (stateless tier)
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name healthcare-api-asg \
  --launch-template LaunchTemplateName=healthcare-api-lt \
  --min-size 2 --max-size 6 --desired-capacity 2 \
  --target-group-arns arn:aws:elasticloadbalancing:...:targetgroup/healthcare-api-tg \
  --vpc-zone-identifier "subnet-aaa,subnet-bbb"
```

## Step 7: Recommended Managed Alternatives (less ops overhead)
- **Airflow** → Amazon MWAA (Managed Workflows for Apache Airflow)
- **Spark** → Amazon EMR Serverless (pay-per-job, no cluster management)
- **FastAPI** → ECS Fargate instead of raw EC2 (no server patching)
- **Frontend** → Vercel or Amplify Hosting

> For a college/portfolio demo, a single `t3.large` running the full `docker-compose.yml`
> stack is sufficient and far cheaper than the fully managed setup above.
