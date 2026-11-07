output "name" {
  description = "Private AKS cluster name."
  value       = azurerm_kubernetes_cluster.this.name
}
output "oidc_issuer_url" {
  description = "Federation issuer, not a token."
  value       = azurerm_kubernetes_cluster.this.oidc_issuer_url
}
