terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

# S3 Buckets
resource "aws_s3_bucket" "data_bucket" {
  bucket = "${var.data_bucket_name}-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "data_bucket_versioning" {
  bucket = aws_s3_bucket.data_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "lambda_bucket" {
  bucket = "${var.lambda_bucket_name}-${random_id.suffix.hex}"
  force_destroy = true
}

# Lambda Configuration
resource "aws_s3_object" "lambda_code" {
  bucket = aws_s3_bucket.lambda_bucket.bucket
  key    = "lambda_function.zip"
  source = "../src/lambda_function.zip"
  etag   = filemd5("../src/lambda_function.zip")
}

resource "aws_lambda_function" "data_ingestor" {
  function_name = "api-data-ingestor-${random_id.suffix.hex}"
  s3_bucket     = aws_s3_bucket.lambda_bucket.bucket
  s3_key        = aws_s3_object.lambda_code.key
  role          = aws_iam_role.lambda_exec.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 30
  depends_on    = [aws_s3_object.lambda_code]

  environment {
    variables = {
      TARGET_BUCKET = aws_s3_bucket.data_bucket.bucket
    }
  }
}

# IAM Roles
resource "aws_iam_role" "lambda_exec" {
  name = "lambda-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Glue Configuration
resource "aws_glue_catalog_database" "main" {
  name = "data-catalog-${random_id.suffix.hex}"
}

resource "aws_iam_role" "glue_role" {
  name = "glue-role-${random_id.suffix.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  name = "glue-s3-policy-${random_id.suffix.hex}"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject"
      ],
      Resource = [
        "${aws_s3_bucket.data_bucket.arn}",
        "${aws_s3_bucket.data_bucket.arn}/*"
      ]
    }]
  })
}

resource "aws_glue_crawler" "articles_crawler" {
  name          = "articles-crawler-${random_id.suffix.hex}"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.main.name

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  s3_target {
    path = "s3://${aws_s3_bucket.data_bucket.bucket}/articles"
  }

  schedule = "cron(0 12 * * ? *)"
}

resource "aws_glue_crawler" "blogs_crawler" {
  name          = "blogs-crawler-${random_id.suffix.hex}"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.main.name

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  s3_target {
    path = "s3://${aws_s3_bucket.data_bucket.bucket}/blogs"
  }

  schedule = "cron(0 12 * * ? *)"
}

resource "aws_glue_crawler" "reports_crawler" {
  name          = "reports-crawler-${random_id.suffix.hex}"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.main.name

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  s3_target {
    path = "s3://${aws_s3_bucket.data_bucket.bucket}/reports"
  }

  schedule = "cron(0 12 * * ? *)"
}

# Athena Workgroup
resource "aws_athena_workgroup" "analytics" {
  name = "athena-workgroup-${random_id.suffix.hex}"

  configuration {
    enforce_workgroup_configuration    = false
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_bucket.bucket}/athena-results/"
    }
  }
  force_destroy = true
}