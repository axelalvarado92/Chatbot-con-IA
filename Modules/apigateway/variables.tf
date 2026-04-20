variable "function_name" {
    description = "Nombre de la función Lambda a integrar con API Gateway"
    type        = string
    default = ""
  
}

variable "lambda_invoke_arn" {
    description = "ARN de la función Lambda a integrar con API Gateway"
    type        = string
    default = ""
}

variable "project_name" {
    description = "Nombre del proyecto"
    type        = string
    default = "Chat_ia"
}

variable "environment" {
    description = "Entorno de despliegue"
    type        = string
    default = "dev"
  
}

variable "region" {
    description = "Región de AWS"
    type        = string
    default = "us-east-1"
}