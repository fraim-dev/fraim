resource "aws_s3_bucket" "test_bucket" {
  bucket = "fraim-test-bucket"

  tags = {
    Name        = "Fraim Test Bucket"
    Environment = "test"
    Project     = "fraim"
  }
}

resource "aws_s3_bucket_ownership_controls" "test_bucket" {
  bucket = aws_s3_bucket.test_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "test_bucket" {
  bucket = aws_s3_bucket.test_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_acl" "test_bucket" {
  bucket = aws_s3_bucket.test_bucket.id
  acl = "public-read"
}
