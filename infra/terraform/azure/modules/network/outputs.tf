output "vnet_id" {
  description = "Virtual network ID."
  value       = azurerm_virtual_network.this.id
}
output "aks_subnet_id" {
  description = "Isolated AKS node subnet ID."
  value       = azurerm_subnet.aks.id
}
output "private_endpoint_subnet_id" {
  description = "Separate private endpoint subnet ID."
  value       = azurerm_subnet.private_endpoints.id
}
