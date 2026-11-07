variable "tenant_id" {
  type        = string
  description = "Entra tenant UUID."
}
variable "vnet_id" {
  type        = string
  description = "Virtual network for private DNS resolution."
}
variable "private_endpoint_subnet_id" {
  type        = string
  description = "Private endpoint subnet."
}
variable "workload_principal_id" {
  type        = string
  description = "Workload managed identity object ID."
}
