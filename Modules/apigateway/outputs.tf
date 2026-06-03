output "api_url" {
  description = "Invoke URL of the API Gateway"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}