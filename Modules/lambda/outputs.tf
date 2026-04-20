output "lambda_invoke_arn" {
    value = aws_lambda_function.lambda_ia.arn
}

output "lambda_function_name" {
    value = aws_lambda_function.lambda_ia.id
}
