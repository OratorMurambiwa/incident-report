variable "subnet_id" {
  type        = string
  description = "AKS node subnet ID."
}
variable "control_plane" {
  type        = object({ id = string, client_id = string, principal_id = string })
  description = "User-assigned control-plane identity metadata."
}
variable "kubelet" {
  type        = object({ id = string, client_id = string, principal_id = string })
  description = "User-assigned kubelet identity metadata."
}
variable "tenant_id" {
  type        = string
  description = "Microsoft Entra tenant UUID."
}
variable "admin_group_object_ids" {
  type        = list(string)
  description = "Existing authorized Entra admin groups."
}
variable "kubernetes_version" {
  type        = string
  description = "Explicit future supported server version."
}
variable "node_vm_size" {
  type        = string
  description = "Billable system node VM SKU."
}
variable "node_count" {
  type        = number
  description = "Fixed node count, no unbounded autoscale."
}
