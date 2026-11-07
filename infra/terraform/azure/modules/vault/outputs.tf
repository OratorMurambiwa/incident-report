output "name" {
  description = "Key Vault name."
  value       = azurerm_key_vault.this.name
}
output "uri" {
  description = "Key Vault URI; no secret contents."
  value       = azurerm_key_vault.this.vault_uri
}
