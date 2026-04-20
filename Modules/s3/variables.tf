variable "tags" {
    description = "Tags para el bucket s3"
    type = map(string)
    default = {}
}

variable "bucket_name" {
    description = "El nombre del bucket s3"
    type = string
  
}