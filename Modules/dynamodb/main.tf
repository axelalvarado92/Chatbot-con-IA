resource "aws_dynamodb_table" "chat_memory" {
  name         = "${var.project_name}-${var.environment}-chat-memory"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }


  tags = {
    Table_Name  = var.table_name
    Environment = var.environment
    Project     = var.project_name
  }
}

