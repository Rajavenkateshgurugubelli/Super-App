module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "superapp-prod-cluster"
  cluster_version = "1.30"

  cluster_endpoint_public_access  = true
  
  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  # Managed Node Groups
  eks_managed_node_group_defaults = {
    instance_types = ["m6i.xlarge", "m5.xlarge"]
  }

  eks_managed_node_groups = {
    core_services = {
      min_size     = 3
      max_size     = 10
      desired_size = 3

      instance_types = ["m6i.xlarge"]
      capacity_type  = "ON_DEMAND"
      
      labels = {
        role = "core-services"
      }
    }
  }

  tags = {
    Environment = "prod"
    Project     = "GlobalGenesisSuperApp"
  }
}
