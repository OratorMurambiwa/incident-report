output "control_plane" {
  description = "Managed identity metadata, never a client secret."
  value       = azurerm_user_assigned_identity.this["control-plane"]
}
output "kubelet" {
  description = "Managed identity metadata, never a client secret."
  value       = azurerm_user_assigned_identity.this["kubelet"]
}
output "workload" {
  description = "Managed identity metadata, never a client secret."
  value       = azurerm_user_assigned_identity.this["workload"]
}
