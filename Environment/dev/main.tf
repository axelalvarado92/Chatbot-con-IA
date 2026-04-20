module "s3"{
    source = "../../Modules/s3"
    bucket_name = "babelviajes-chatbot-47148"
    
    tags = {
        Environment = "dev"
        Project     = "chatbot-ia"
    }
    
}

module "chat_ia" {
    source = "../../Modules/lambda"
    function_name = "${var.project_name}-${var.environment}-chat-ia"
    handler = "lambda_function.lambda_handler"
    filename         = data.archive_file.chat_ia_zip.output_path
    source_code_hash = data.archive_file.chat_ia_zip.output_base64sha256
    bucket_arn = module.s3.bucket_arn

    memory_size = 256
    timeout = 30

    environment_variables = {
        BUCKET_NAME = module.s3.bucket_name
        KNOWLEDGE_FILE = "knowledge.json"
        OPENAI_API_KEY = var.open_api_key
    }
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


  
