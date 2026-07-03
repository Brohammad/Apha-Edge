"""Minimal Terraform stub for AlphaEdge AWS deployment.

Full module wiring (VPC, ECS, RDS, ElastiCache) is documented in README.md.
Apply with: terraform init && terraform apply -var-file=prod.tfvars
"""

variable "project" {
  type    = string
  default = "alphaedge"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}
