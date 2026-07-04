output "assistant_table_name" {
  value = aws_dynamodb_table.assistant_config.name
}

output "assistant_table_arn" {
  value = aws_dynamodb_table.assistant_config.arn
}