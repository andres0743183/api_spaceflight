variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "data_bucket_name" {
  description = "Nombre del bucket S3 para datos"
  type        = string
}

variable "lambda_bucket_name" {
  description = "Nombre del bucket S3 para código Lambda"
  type        = string
}

variable "tags" {
  description = "Tags para recursos"
  type        = map(string)
  default     = {}
}