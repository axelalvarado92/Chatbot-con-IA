resource "aws_dynamodb_table" "assistant_config" {

  name         = "${var.project_name}-${var.environment}-assistant-config"

  billing_mode = "PAY_PER_REQUEST"

  hash_key = "config_id"

  attribute {
    name = "config_id"
    type = "S"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}