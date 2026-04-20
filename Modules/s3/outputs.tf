output "bucket_name" {
    value = aws_s3_bucket.bucket_knowledge.id
  
}

output "bucket_arn" {
    value = aws_s3_bucket.bucket_knowledge.arn
  
}