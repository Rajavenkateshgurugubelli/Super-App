variable "aws_region" {
  description = "AWS Region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Target environment (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "eks_node_min_size" {
  description = "Minimum number of nodes in EKS managed node group"
  type        = number
  default     = 2
}

variable "eks_node_max_size" {
  description = "Maximum number of nodes in EKS managed node group"
  type        = number
  default     = 4
}

variable "eks_node_desired_size" {
  description = "Desired number of nodes in EKS managed node group"
  type        = number
  default     = 2
}
