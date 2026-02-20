variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region (e.g., us-central1)"
  type        = string
  default     = "us-central1"
}

variable "backend_image" {
  description = "Docker image for Backend Service"
  type        = string
}

variable "gateway_image" {
  description = "Docker image for Gateway Service"
  type        = string
}

variable "frontend_image" {
  description = "Docker image for Frontend Service"
  type        = string
}
