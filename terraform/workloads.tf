# =============================================================================
# Persistent Storage for Database and Screenshots
# =============================================================================

resource "cpln_volume_set" "booking_data" {
  gvc         = data.cpln_gvc.save30.name
  name        = "${var.project_name}-data"
  description = "Persistent storage for booking database and screenshots"

  tags = var.common_tags

  initial_capacity = 10  # 10GB

  performance_class = "general-purpose-ssd"

  file_system_type = "ext4"
}

# =============================================================================
# Estelle Manor Padel Booking Workload
# =============================================================================

resource "cpln_workload" "padel_booking" {
  gvc         = data.cpln_gvc.save30.name
  name        = var.project_name
  description = "Estelle Manor Padel Court Booking Automation"
  type        = "standard"

  tags = merge(
    var.common_tags,
    {
      service     = "padel-booking"
      environment = var.environment
    }
  )

  identity_link = cpln_identity.estelle_identity.self_link

  container {
    name   = "booking"
    image  = local.estelle_image

    cpu    = var.cpu
    memory = var.memory

    ports {
      number   = 8000
      protocol = "http"
    }

    env = {
      ESTELLE_USERNAME             = var.estelle_username
      ESTELLE_PASSWORD             = var.estelle_password
      DISCORD_WEBHOOK_URL          = var.discord_webhook_url
      DRY_RUN                      = tostring(var.dry_run)
      LOG_LEVEL                    = var.log_level
      DATABASE_PATH                = "./data/estelle.db"
      BROWSER_STATE_PATH           = "./data/browser_state.json"
      PRE_LOGIN_MINUTES            = tostring(var.pre_login_minutes)
      API_HOST                     = "0.0.0.0"
      API_PORT                     = "8000"
      EVENTS_MONITORING_ENABLED    = tostring(var.events_monitoring_enabled)
      EVENTS_CHECK_INTERVAL_HOURS  = tostring(var.events_check_interval_hours)
    }

    readiness_probe {
      http_get {
        path   = "/health"
        port   = 8000
        scheme = "HTTP"
      }
      initial_delay_seconds = 10
      period_seconds        = 10
    }

    liveness_probe {
      http_get {
        path   = "/health"
        port   = 8000
        scheme = "HTTP"
      }
      initial_delay_seconds = 15
      period_seconds        = 20
    }

    # Note: Persistent storage temporarily disabled - focusing on headless browser fix
    # volume {
    #   uri  = "cpln://volumeset/${cpln_volume_set.booking_data.name}"
    #   path = "/app/data"
    # }
  }

  options {
    capacity_ai     = false
    timeout_seconds = 300
    debug           = false

    autoscaling {
      metric              = "disabled"
      target              = 1
      max_scale           = var.max_replicas
      min_scale           = var.min_replicas
      max_concurrency     = 1
      scale_to_zero_delay = 300
    }
  }

  firewall_spec {
    external {
      inbound_allow_cidr      = var.allowed_cidrs
      outbound_allow_cidr     = ["0.0.0.0/0"]  # Allow all outbound for Estelle Manor and Discord
      outbound_allow_hostname = []
    }
    internal {
      inbound_allow_type     = "same-gvc"
      inbound_allow_workload = []
    }
  }
}
