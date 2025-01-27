output "data_bucket_name" {
  value = aws_s3_bucket.data_bucket.bucket
}

output "lambda_function_name" {
  value = aws_lambda_function.data_ingestor.function_name
}

output "articles_crawler_name" {
  value = aws_glue_crawler.articles_crawler.name
}

output "blogs_crawler_name" {
  value = aws_glue_crawler.blogs_crawler.name
}

output "reports_crawler_name" {
  value = aws_glue_crawler.reports_crawler.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.analytics.name
}