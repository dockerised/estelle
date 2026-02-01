# =============================================================================
# Organization & Project Configuration
# =============================================================================

variable "org_name" {
  description = "Control Plane organization name"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "gc-estelle"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# =============================================================================
# GVC Configuration
# =============================================================================

variable "gvc_name" {
  description = "Name of the Global Virtual Cloud"
  type        = string
  default     = "save30-gvc"
}

variable "locations" {
  description = "List of locations to deploy to"
  type        = list(string)
  default     = ["aws-eu-west-2"]
}

# =============================================================================
# Container Images
# =============================================================================

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "estelle_image" {
  description = "Estelle booking container image (leave empty to use org registry)"
  type        = string
  default     = ""
}

# =============================================================================
# Resource Configuration
# =============================================================================

variable "cpu" {
  description = "CPU allocation for booking service"
  type        = string
  default     = "500m"
}

variable "memory" {
  description = "Memory allocation for booking service"
  type        = string
  default     = "1Gi"
}

# =============================================================================
# Scaling Configuration
# =============================================================================

variable "min_replicas" {
  description = "Minimum number of replicas"
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum number of replicas"
  type        = number
  default     = 1
}

# =============================================================================
# Environment Variables & Secrets
# =============================================================================

variable "estelle_username" {
  description = "Estelle Manor username"
  type        = string
  sensitive   = true
}

variable "estelle_password" {
  description = "Estelle Manor password"
  type        = string
  sensitive   = true
}

variable "discord_webhook_url" {
  description = "Discord webhook URL for notifications"
  type        = string
  sensitive   = true
}

variable "dry_run" {
  description = "Run in dry-run mode (no actual bookings)"
  type        = bool
  default     = false
}

variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

variable "pre_login_minutes" {
  description = "Minutes before midnight to login"
  type        = number
  default     = 10
}

variable "events_monitoring_enabled" {
  description = "Enable What's On page monitoring"
  type        = bool
  default     = false
}

variable "events_check_interval_hours" {
  description = "Hours between event checks"
  type        = number
  default     = 6
}

# =============================================================================
# Network Configuration
# =============================================================================

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to access the service"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# =============================================================================
# Tags
# =============================================================================

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    managed_by = "terraform"
    project    = "gc-estelle"
  }
}
