resource "azurerm_key_vault" "this" {
  name                          = var.name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  enable_rbac_authorization     = true
  public_network_access_enabled = false
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  network_acls {
    bypass         = "None"
    default_action = "Deny"
  }
  tags = var.tags
}
resource "azurerm_private_dns_zone" "this" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}
resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  name                  = "${var.name}-dns"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.this.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}
resource "azurerm_private_endpoint" "this" {
  name                = "${var.name}-endpoint"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "keyvault"
    private_connection_resource_id = azurerm_key_vault.this.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "keyvault"
    private_dns_zone_ids = [azurerm_private_dns_zone.this.id]
  }
  tags = var.tags
}
resource "azurerm_role_assignment" "read_secrets" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.workload_principal_id
  principal_type       = "ServicePrincipal"
}
