# =============================================================================
# Estelle Manor Padel Booking - Control Plane Configuration
# =============================================================================

# Organization Configuration
org_name = "george-crosby-015c08"

# Project Configuration
project_name = "gc-estelle"
environment  = "dev"

# GVC Configuration (using existing dev GVC)
gvc_name  = "dev"
locations = ["aws-eu-central-1"]

# Image Configuration
image_tag     = "latest"
estelle_image = "/org/george-crosby-015c08/image/gc-estelle-padel-booking:latest"

# Resource Configuration
cpu    = "500m"
memory = "1Gi"

# Scaling Configuration (KEDA cron-based: 0 replicas except 11:40PM-12:15AM)
min_replicas = 0  # Scale to zero when not in booking window
max_replicas = 1  # One replica during booking window

# Application Settings
dry_run                    = false
log_level                  = "INFO"
pre_login_minutes          = 10
events_monitoring_enabled  = true
events_check_interval_hours = 6

# Network Configuration
allowed_cidrs = ["0.0.0.0/0"]

# Common Tags
common_tags = {
  managed_by = "terraform"
  project    = "gc-estelle"
  team       = "personal"
}

# IMPORTANT: Set these via environment variables or secrets.tfvars:
# export TF_VAR_estelle_username='your.email@example.com'
# export TF_VAR_estelle_password='your_password'
# export TF_VAR_discord_webhook_url='https://discord.com/api/webhooks/...'
