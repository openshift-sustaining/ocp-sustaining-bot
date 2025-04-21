provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "custom_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name  = var.vpc_name
    Owner = var.vpc_owner
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.custom_vpc.id

  tags = {
    Name  = "${var.vpc_name}-igw"
    Owner = var.vpc_owner
  }
}

# Public Subnet 1
resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.custom_vpc.id
  cidr_block              = var.public_subnet_cidr_1
  availability_zone       = var.public_subnet_az_1
  map_public_ip_on_launch = true

  tags = {
    Name  = "${var.vpc_name}-public-subnet-1"
    Owner = var.vpc_owner
  }
}

# Public Subnet 2
resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.custom_vpc.id
  cidr_block              = var.public_subnet_cidr_2
  availability_zone       = var.public_subnet_az_2
  map_public_ip_on_launch = true

  tags = {
    Name  = "${var.vpc_name}-public-subnet-2"
    Owner = var.vpc_owner
  }
}

# Public Route Table for Routing to Internet Gateway
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.custom_vpc.id

  tags = {
    Name  = "${var.vpc_name}-public-rt"
    Owner = var.vpc_owner
  }
}

# Route for Internet Access
resource "aws_route" "public_internet_access" {
  route_table_id         = aws_route_table.public_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
  depends_on = [aws_internet_gateway.igw]
}

# Associate Route Table with Public Subnets
resource "aws_route_table_association" "public_assoc_1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_assoc_2" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_rt.id
}

# Security Group for SSH Access
resource "aws_security_group" "allow_ssh" {
  name        = "allow_ssh"
  description = "Allow SSH access from anywhere"
  vpc_id      = aws_vpc.custom_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Allow SSH from anywhere
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"  # Allow all outbound traffic
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name  = "Allow SSH"
    Owner = var.vpc_owner
  }
}

# Output the VPC ID
output "vpc_id" {
  description = "The ID of the custom VPC"
  value       = aws_vpc.custom_vpc.id
}

# Output the Public Subnets IDs
output "public_subnet_id_1" {
  description = "The ID of the first public subnet"
  value       = aws_subnet.public_subnet_1.id
}

output "public_subnet_id_2" {
  description = "The ID of the second public subnet"
  value       = aws_subnet.public_subnet_2.id
}

# Output the Security Group ID
output "security_group_id" {
  description = "The ID of the security group"
  value       = aws_security_group.allow_ssh.id
}

