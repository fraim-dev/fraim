resource "aws_iam_role" "test_role_container" {
  name                = "test_role_container"
  assume_role_policy  = data.aws_iam_policy_document.instance_assume_role_policy1.json
  managed_policy_arns = [aws_iam_policy.policy_two.arn]
}

resource "aws_iam_role" "test_role_instance_profile" {
  name                = "test_role_container_policy"
  assume_role_policy  = data.aws_iam_policy_document.instance_assume_role_policy2.json
  managed_policy_arns = [aws_iam_policy.policy_one.arn, aws_iam_policy.policy_three.arn]
}

resource "aws_iam_policy" "policy_one" {
  name = "policy-618033"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["ec2:Describe*"]
        Effect   = "Allow"
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_policy" "policy_two" {
  name = "policy-381966"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = [
            "s3:ListAllMyBuckets",
            "s3:ListBucket",
            "s3:HeadBucket",
            "s3:Write*"]
        Effect   = "Allow"
        Resource = "fraim-*"
      },
    ]
  })
}

resource "aws_iam_policy" "policy_three" {
  name = "policy-381966"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:GetRepositoryPolicy",
            "ecr:DescribeRepositories",
            "ecr:ListImages"]
        Effect   = "Allow"
        Resource = "*"
      },
    ]
  })
}