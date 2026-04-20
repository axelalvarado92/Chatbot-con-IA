resource "aws_lambda_function" "lambda_ia" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_ia_role.arn
  handler       = var.handler
  runtime       = "python3.11"

  memory_size   = var.memory_size
  timeout       = var.timeout

  filename         = var.filename
  source_code_hash = var.source_code_hash

  environment {
    variables = var.environment_variables
  }
}

resource "aws_iam_role" "lambda_ia_role" {
    name = "${var.project_name}-${var.environment}-lambda-ia-role"
    
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
        {
            Action = "sts:AssumeRole"
            Effect = "Allow"
            Principal = {
            Service = "lambda.amazonaws.com"
            }
        }
        ]
    })
}

data "aws_iam_policy_document" "lambda_policy_doc" {
    statement {
        sid = "s3Access"
        effect = "Allow"
        actions = [
            "s3:GetObject"
            ]
        
        resources = [ 
            "${var.bucket_arn}/*"
            ]
        
    }
  
}

resource "aws_iam_policy" "lambda_policy" {
    name   = "${var.project_name}-${var.environment}-lambda-ia-policy"
    policy = data.aws_iam_policy_document.lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
    role       = aws_iam_role.lambda_ia_role.name
    policy_arn = aws_iam_policy.lambda_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
    role       = aws_iam_role.lambda_ia_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

}