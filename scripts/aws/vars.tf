variable "aws_region" {
  description = "The AWS region to deploy the VPC"
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_name" {
  description = "Name tag for the VPC"
  type        = string
  default     = "openshift-sustaining-vpc"
}

variable "vpc_owner" {
  description = "Resource Owner"
  type        = string
  default     = "openshift sustaining slack bot"
}

variable "public_subnet_cidr_1" {
  description = "CIDR block for the first public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_cidr_2" {
  description = "CIDR block for the second public subnet"
  type        = string
  default     = "10.0.2.0/24"
}

variable "public_subnet_az_1" {
  description = "Availability Zone for the first public subnet"
  type        = string
  default     = "ap-south-1a"
}

variable "public_subnet_az_2" {
  description = "Availability Zone for the second public subnet"
  type        = string
  default     = "ap-south-1b"
}

