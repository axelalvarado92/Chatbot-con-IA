resource "aws_s3_bucket" "bucket_knowledge" {
    bucket = var.bucket_name

    force_destroy = true

    tags = var.tags
  
}

# RECURSO PARA SUBIR EL ARCHIVO
resource "aws_s3_object" "knowledge_file" {
  bucket       = aws_s3_bucket.bucket_knowledge.id
  key          = var.knowledge_file_name
  source       = var.knowledge_file_path
  content_type = "application/json"
  
  # Crucial para que Terraform detecte cambios en el contenido del JSON
  etag = filemd5(var.knowledge_file_path)
}

resource "aws_s3_object" "prompt" {
  bucket = aws_s3_bucket.bucket_knowledge.id
  key    = var.prompt_file_name
  source = var.prompt_file_path
  content_type = "application/json"

  etag = filemd5(var.prompt_file_path)
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