variable "project_name" {
    description = "The name of the project"
    type = string
    default = "chatbot"
  
}

variable "environment" {
    description = "The environment name (e.g., dev, staging, prod)"
    type = string
}

variable "table_name" {
    description = "The name of the DynamoDB table for assistant configuration"
    type = string
}