# Backend Service
resource "google_cloud_run_service" "backend" {
  name     = "superapp-backend"
  location = var.region

  template {
    spec {
      containers {
        image = var.backend_image
        ports {
          container_port = 50051 # gRPC
        }
        env {
          name  = "DATABASE_URL"
          # For Cloud SQL, connect via socket or private IP. Using SQLite/file for demo simplicity or generic connection string var.
          value = "sqlite:///./superapp.db" 
        }
        # Enable HTTP/2 for gRPC
        ports {
          name = "h2c" 
          container_port = 50051
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Gateway Service
resource "google_cloud_run_service" "gateway" {
  name     = "superapp-gateway"
  location = var.region

  template {
    spec {
      containers {
        image = var.gateway_image
        ports {
          container_port = 8000
        }
        env {
          name  = "GRPC_HOST"
          # Cloud Run URL (trim https:// prefix in code, or here)
          value = replace(google_cloud_run_service.backend.status[0].url, "https://", "")
        }
        env {
          name  = "GRPC_SECURE"
          value = "true"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_cloud_run_service.backend]
}

# Frontend Service
resource "google_cloud_run_service" "frontend" {
  name     = "superapp-frontend"
  location = var.region

  template {
    spec {
      containers {
        image = var.frontend_image
        ports {
          container_port = 8080
        }
        env {
          name  = "GATEWAY_URL"
          value = google_cloud_run_service.gateway.status[0].url
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_cloud_run_service.gateway]
}

# Allow unauthenticated invocation for demo purposes
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth_frontend" {
  location    = google_cloud_run_service.frontend.location
  project     = google_cloud_run_service.frontend.project
  service     = google_cloud_run_service.frontend.name
  policy_data = data.google_iam_policy.noauth.policy_data
}

resource "google_cloud_run_service_iam_policy" "noauth_gateway" {
  location    = google_cloud_run_service.gateway.location
  project     = google_cloud_run_service.gateway.project
  service     = google_cloud_run_service.gateway.name
  policy_data = data.google_iam_policy.noauth.policy_data
}

# Backend can be restricted to only be invoked by Gateway via IAM if using Cloud Run invoker
# For now, leaving opened or default (private by usually default unless open)
# But note: earlier setup allowed unauth. Let's keep backend unauth for easy gRPC debug if desired or align with security.
# For simplicity in demo, allow unauth for backend too (Phase 15 will implement service mesh/mTLS).
resource "google_cloud_run_service_iam_policy" "noauth_backend" {
  location    = google_cloud_run_service.backend.location
  project     = google_cloud_run_service.backend.project
  service     = google_cloud_run_service.backend.name
  policy_data = data.google_iam_policy.noauth.policy_data
}
