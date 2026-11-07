output "id" {
  description = "Scoped AcrPull assignment target."
  value       = azurerm_container_registry.this.id
}
output "login_server" {
  description = "ACR hostname, not credentials."
  value       = azurerm_container_registry.this.login_server
}
