variable "region" {
    description = "Región de AWS donde se desplegarán los recursos"
    type = string
    default = "us-east-1"
  
}

variable "project_name" {
    description = "Nombre del proyecto"
    type = string
    default = "chatbot-ia"
  
}

variable "environment" {
    description = "Entorno de despliegue"
    type = string
    default = "dev"
  
}

variable "open_api_key" {
    description = "Clave de API de OpenAI"
    type = string
  
}

variable "bitrix_webhook_url" {
    description = "URL del webhook de Bitrix24"
    type = string
  
}

variable "client_name" {
    description = "Nombre del cliente o empresa"
    type = string
    
}

variable "whatcrm_instance" {
    description = "Instancia de WhatCRM"
    type = string
      
}

variable "whatcrm_token" {
    description = "Token de WhatCRM"
    type = string
      
}

variable "debug_whatsapp" {
    description = "Habilitar modo de depuración para WhatsApp"
    type = bool
    default = false
}

variable "send_whatsapp_messages" {
    description = "Habilitar el envío de mensajes de WhatsApp"
    type = bool
    default = true
}

