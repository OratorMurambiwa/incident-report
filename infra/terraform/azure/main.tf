locals {
  name = "${var.name_prefix}-${var.unique_suffix}"
  tags = merge(var.tags, { project = "IncidentIQ", environment = "future-development", managed_by = "Terraform" })
}
resource "azurerm_resource_group" "this" {
  name     = "${local.name}-rg"
  location = var.location
  tags     = local.tags
}
module "network" {
  source              = "./modules/network"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}
module "identities" {
  source              = "./modules/identities"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}
module "registry" {
  source              = "./modules/registry"
  name                = "${var.name_prefix}${var.unique_suffix}acr"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}
resource "azurerm_role_assignment" "node_network" {
  scope                = module.network.aks_subnet_id
  role_definition_name = "Network Contributor"
  principal_id         = module.identities.control_plane.principal_id
  principal_type       = "ServicePrincipal"
}
resource "azurerm_role_assignment" "kubelet_operator" {
  scope                = module.identities.kubelet.id
  role_definition_name = "Managed Identity Operator"
  principal_id         = module.identities.control_plane.principal_id
  principal_type       = "ServicePrincipal"
}
resource "azurerm_role_assignment" "registry_pull" {
  scope                = module.registry.id
  role_definition_name = "AcrPull"
  principal_id         = module.identities.kubelet.principal_id
  principal_type       = "ServicePrincipal"
}
module "aks" {
  source                 = "./modules/aks"
  name                   = local.name
  location               = var.location
  resource_group_name    = azurerm_resource_group.this.name
  subnet_id              = module.network.aks_subnet_id
  control_plane          = module.identities.control_plane
  kubelet                = module.identities.kubelet
  tenant_id              = var.tenant_id
  admin_group_object_ids = var.admin_group_object_ids
  kubernetes_version     = var.kubernetes_version
  node_vm_size           = var.node_vm_size
  node_count             = var.node_count
  tags                   = local.tags
  depends_on             = [azurerm_role_assignment.node_network, azurerm_role_assignment.kubelet_operator, azurerm_role_assignment.registry_pull]
}
module "vault" {
  source                     = "./modules/vault"
  name                       = "${local.name}-kv"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = var.tenant_id
  vnet_id                    = module.network.vnet_id
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  workload_principal_id      = module.identities.workload.principal_id
  tags                       = local.tags
}
resource "azurerm_federated_identity_credential" "keyvault" {
  name                = "incidentiq-keyvault"
  resource_group_name = azurerm_resource_group.this.name
  parent_id           = module.identities.workload.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = module.aks.oidc_issuer_url
  subject             = "system:serviceaccount:${var.kubernetes_namespace}:incidentiq-keyvault"
}
