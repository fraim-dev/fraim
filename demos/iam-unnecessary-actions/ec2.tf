resource "aws_instance" "example" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  iam_instance_profile = aws_iam_instance_profile.test_role_instance_profile.name
}
