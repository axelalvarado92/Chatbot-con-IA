variable "tags" {
    description = "Tags para el bucket s3"
    type = map(string)
    default = {}
}

variable "bucket_name" {
    description = "El nombre del bucket s3"
    type = string
  
}

variable "knowledge_file_name" {
    description = "El nombre del archivo de conocimiento en el bucket s3"
    type = string
}

variable "knowledge_file_path" {
    description = "La ruta local del archivo de conocimiento para subir a s3"
    type = string
}