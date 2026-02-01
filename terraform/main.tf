# =============================================================================
# Estelle Manor Padel Booking System - Control Plane Infrastructure
# =============================================================================

locals {
  # Image URI - use provided or default to org registry
  estelle_image = var.estelle_image != "" ? var.estelle_image : "/org/${var.org_name}/image/gc-estelle-padel-booking:${var.image_tag}"
}

# =============================================================================
# Use Existing GVC
# =============================================================================

data "cpln_gvc" "save30" {
  name = var.gvc_name
}

# =============================================================================
# Workload Identity
# =============================================================================

resource "cpln_identity" "estelle_identity" {
  gvc         = data.cpln_gvc.save30.name
  name        = "${var.project_name}-identity"
  description = "Identity for Estelle Manor Padel Booking System"
  tags        = var.common_tags
}

# =============================================================================
# Outputs
# =============================================================================

output "gvc_name" {
  description = "Name of the GVC"
  value       = data.cpln_gvc.save30.name
}

output "booking_endpoint" {
  description = "Booking service endpoint URL"
  value       = "https://${var.project_name}.${data.cpln_gvc.save30.name}.cpln.app"
}
