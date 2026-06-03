variable "project_name" {
    description = "Nombre del proyecto"
    type        = string
    default = "chatbot_ia"
  
}

variable "environment" {
    description = "Entorno de despliegue"
    type        = string
    default = "dev"
  
}

variable table_name {
    description = "Nombre de la tabla DynamoDB para almacenar la memoria del chatbot"
    type        = string
}