output "datalake_bucket_name" {
  value = aws_s3_bucket.datalake.id
}

output "datalake_bucket_arn" {
  value = aws_s3_bucket.datalake.arn
}

output "scripts_bucket_name" {
  value = aws_s3_bucket.scripts.id
}
