variable "subscription_id" {
  type        = string
  description = "Future Azure subscription UUID; identifier only, never a credential."
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "Invalid subscription_id; see the documented constraints."
  }
}
variable "tenant_id" {
  type        = string
  description = "Future Microsoft Entra tenant UUID; identifier only."
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.tenant_id))
    error_message = "Invalid tenant_id; see the documented constraints."
  }
}
variable "name_prefix" {
  type        = string
  description = "Short lowercase resource-name prefix."
  default     = "incidentiq"
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,9}$", var.name_prefix))
    error_message = "Invalid name_prefix; see the documented constraints."
  }
}
variable "unique_suffix" {
  type        = string
  description = "Globally unique lowercase alphanumeric suffix for ACR and Key Vault."
  validation {
    condition     = can(regex("^[a-z0-9]{4,10}$", var.unique_suffix))
    error_message = "Invalid unique_suffix; see the documented constraints."
  }
}
variable "location" {
  type        = string
  description = "Azure region; future operator must check SKU and Kubernetes availability."
  default     = "eastus"
}
variable "admin_group_object_ids" {
  type        = list(string)
  description = "Existing Entra group UUIDs granted AKS administration; no local admin credentials."
  validation {
    condition     = length(var.admin_group_object_ids) > 0 && alltrue([for id in var.admin_group_object_ids : can(regex("^[0-9a-fA-F-]{36}$", id))])
    error_message = "Invalid admin_group_object_ids; see the documented constraints."
  }
}
variable "kubernetes_version" {
  type        = string
  description = "Explicit supported AKS version; check region support before any future plan."
  default     = "1.35"
}
variable "node_vm_size" {
  type        = string
  description = "One system node; D4s_v5 provides CPU/RAM headroom but is billable."
  default     = "Standard_D4s_v5"
}
variable "node_count" {
  type        = number
  description = "Bounded fixed node count; one is economical but not highly available."
  default     = 1
  validation {
    condition     = var.node_count >= 1 && var.node_count <= 3 && floor(var.node_count) == var.node_count
    error_message = "Invalid node_count; see the documented constraints."
  }
}
variable "kubernetes_namespace" {
  type        = string
  description = "Namespace used by workload federation and Azure Kustomize overlay."
  default     = "incidentiq-azure"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,61}[a-z0-9]$", var.kubernetes_namespace))
    error_message = "Invalid kubernetes_namespace; see the documented constraints."
  }
}
variable "tags" {
  type        = map(string)
  description = "Additional nonsecret resource tags."
  default     = {}
}

# Validate names/identifiers locally, without data-source access to Azure.
