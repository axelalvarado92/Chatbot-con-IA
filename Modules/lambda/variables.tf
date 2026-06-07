variable "project_name" {
    description = "The name of the project"
    type        = string
    default = "Chatbot_ia"
  
}

variable "environment" {
    description = "The environment where the resources will be deployed"
    type        = string
    default = "dev"
  
}

variable "bucket_arn" {
    description = "The ARN of the S3 bucket for Lambda access"
    type        = string
  
}
variable "function_name" {
    description = "The name of the Lambda function"
    type        = string
}

variable "handler" {
    description = "The handler for the Lambda function"
    type        = string
}

variable "filename" {
    description = "The path to the Lambda deployment package"
    type        = string
}

variable "source_code_hash" {
    description = "The base64-encoded SHA256 hash of the Lambda deployment package"
    type        = string
}

variable "environment_variables" {
    description = "A map of environment variables for the Lambda function"
    type        = map(string)
    default     = {}
}

variable "memory_size" {
    description = "Tamaño de memoria de Lambda"
    type = number
  
}

variable "timeout" {
    description = "Tiempo de procesamiento"
    type = number
  
}

variable "dynamodb_table_arn" {
    description = "The ARN of the DynamoDB table for Lambda access"
    type        = string
}

variable "layers" {
    description = "A list of Lambda layers to attach to the function"
    type        = list(string)
    default     = []
}

variable "audit_bucket_arn" {
    description = "The ARN of the S3 bucket for audit logs"
    type        = string
}