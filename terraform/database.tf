resource "google_sql_database_instance" "master" {
  name             = "superapp-db-instance"
  database_version = "POSTGRES_14"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    user_labels = {
      app = "superapp"
    }

    # Public IP for simplicity in demo. In prod, use Private IP + VPC Peering.
    ip_configuration {
      ipv4_enabled    = true
      # private_network = google_compute_network.vpc.id
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0" # Allow from anywhere (Dev only!)
      }
    }
  }
  deletion_protection  = false # For dev
}

resource "google_sql_database" "database" {
  name     = "superapp_db"
  instance = google_sql_database_instance.master.name
}

resource "google_sql_user" "users" {
  name     = "superapp_user"
  instance = google_sql_database_instance.master.name
  password = "changeme123" # In real usage, use Secret Manager
}

output "connection_name" {
  value = google_sql_database_instance.master.connection_name
}
