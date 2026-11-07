output "resource_group_name" {
  description = "Resource group name; no credentials."
  value       = azurerm_resource_group.this.name
}
output "aks_name" {
  description = "AKS cluster name; private API needs private-network access."
  value       = module.aks.name
}
output "acr_login_server" {
  description = "Authenticated public ACR endpoint; admin password disabled."
  value       = module.registry.login_server
}
output "key_vault_uri" {
  description = "Key Vault URI, reachable through its private endpoint."
  value       = module.vault.uri
}
output "kustomize_config" {
  description = "Nonsecret identity/registry references consumed by scripts/render-azure-overlay.py."
  value       = { namespace = var.kubernetes_namespace, tenant_id = var.tenant_id, client_id = module.identities.workload.client_id, key_vault_name = module.vault.name, registry = module.registry.login_server }
}
