resource "aws_security_group" "example" {
  name        = "example_security_group"
  description = "Example Description"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port        = 5938
    to_port          = 5938
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}
