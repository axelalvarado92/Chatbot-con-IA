resource "aws_s3_bucket" "audit" {
  bucket = "${var.project_name}-${var.client_name}-audit"
}

module "s3" {
    source      = "../../Modules/s3"
    bucket_name = "${var.client_name}-${var.environment}-assets-47148"
    
    # Configuramos el archivo desde la nueva carpeta assets
    knowledge_file_name = "knowledge.json"
    knowledge_file_path = "${path.root}/../../assets/${var.client_name}/knowledge.json"

    prompt_file_name = "prompt.json"
    prompt_file_path = "${path.root}/../../assets/${var.client_name}/prompt.json"

    tags = {
        Environment = var.client_name
        Project     = var.project_name
    }
}


module "chat_ia" {
    source = "../../Modules/lambda"
    function_name = "${var.client_name}-${var.environment}-chat-ia"
    handler = "lambda_function.lambda_handler"
    filename         = data.archive_file.chat_ia_zip.output_path
    source_code_hash = data.archive_file.chat_ia_zip.output_base64sha256
    bucket_arn = module.s3.bucket_arn
    dynamodb_table_arn = module.dynamodb.chat_memory_table_arn

    layers = [aws_lambda_layer_version.openai_layer.arn]

    audit_bucket_arn = aws_s3_bucket.audit.arn
    
    memory_size = 256
    timeout = 30

    environment_variables = {
        BUCKET_NAME        = module.s3.bucket_name
        OPENAI_API_KEY     = var.open_api_key
        TABLE_NAME         = module.dynamodb.chat_memory_table_name
        BITRIX_WEBHOOK_URL = var.bitrix_webhook_url
        KNOWLEDGE_FILE     = "knowledge.json"
        PROMPT_FILE        = "prompt.json"
        BUSINESS_TYPE      = var.business_type
        AUDIT_BUCKET       = aws_s3_bucket.audit.bucket

    }
}
    
data "archive_file" "openai_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../build/layer_openai"
  output_path = "${path.module}/../../build/openai_layer.zip"
}

resource "aws_lambda_layer_version" "openai_layer" {
  filename            = data.archive_file.openai_layer_zip.output_path
  layer_name          = "openai-requests-layer"
  compatible_runtimes = ["python3.11"] 
  source_code_hash    = data.archive_file.openai_layer_zip.output_base64sha256
}

data "archive_file" "chat_ia_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../Lambdas/knowledge_ia"
  output_path = "../../build/knowledge_ia.zip"
}

module "api_gateway" {
    source = "../../Modules/apigateway"
    function_name = module.chat_ia.lambda_function_name
    lambda_invoke_arn = module.chat_ia.lambda_invoke_arn
}

module "dynamodb" {
    source = "../../Modules/dynamodb"
    table_name = "${var.client_name}-chat-memory"
}

  
