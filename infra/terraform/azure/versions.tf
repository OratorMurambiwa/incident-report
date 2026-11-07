terraform {
  required_version = "~> 1.12.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "= 4.30.0" }
  }
}
provider "azurerm" {
  features {
    key_vault { purge_soft_delete_on_destroy = false }
  }
  subscription_id                 = var.subscription_id
  tenant_id                       = var.tenant_id
  resource_provider_registrations = "none"
  use_cli                         = false
  use_msi                         = false
  use_oidc                        = true
}
