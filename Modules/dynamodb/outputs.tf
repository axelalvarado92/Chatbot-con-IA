output "chat_memory_table_name" {
  value = aws_dynamodb_table.chat_memory.name
}

output "chat_memory_table_arn" {
  value = aws_dynamodb_table.chat_memory.arn
}