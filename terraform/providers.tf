terraform {
  required_version = ">= 1.0"

  required_providers {
    cpln = {
      source  = "controlplane-com/cpln"
      version = "~> 1.0"
    }
  }
}

provider "cpln" {
  org = var.org_name
}
