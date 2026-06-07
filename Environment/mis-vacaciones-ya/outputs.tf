output "api_url" {
    value = module.api_gateway.api_url
  
}

data "aws_caller_identity" "current" {}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}