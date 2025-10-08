resource aws_security_group "example" {
    name = "example_security_group"
    description = "Example Description"
    vpc_id = aws_vpc.main.id

    ingress {
        from_port = 5432
        to_port = 5432
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}
