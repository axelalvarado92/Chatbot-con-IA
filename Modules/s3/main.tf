resource "aws_s3_bucket" "bucket_knowledge" {
    bucket = var.bucket_name

    tags = var.tags
  
}

resource "aws_s3_bucket_public_access_block" "s3_knowledge_block" {
  bucket = aws_s3_bucket.bucket_knowledge.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "s3_knowledge_versioning" {
  bucket = aws_s3_bucket.bucket_knowledge.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_knowledge_encryption" {
  bucket = aws_s3_bucket.bucket_knowledge.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}