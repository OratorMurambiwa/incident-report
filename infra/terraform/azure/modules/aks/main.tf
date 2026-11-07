resource "azurerm_kubernetes_cluster" "this" {
  name                                = "${var.name}-aks"
  resource_group_name                 = var.resource_group_name
  location                            = var.location
  dns_prefix                          = var.name
  kubernetes_version                  = var.kubernetes_version
  sku_tier                            = "Free"
  private_cluster_enabled             = true
  private_cluster_public_fqdn_enabled = false
  local_account_disabled              = true
  role_based_access_control_enabled   = true
  oidc_issuer_enabled                 = true
  workload_identity_enabled           = true
  azure_policy_enabled                = true
  default_node_pool {
    name                        = "system"
    node_count                  = var.node_count
    vm_size                     = var.node_vm_size
    vnet_subnet_id              = var.subnet_id
    os_disk_type                = "Managed"
    os_disk_size_gb             = 64
    max_pods                    = 30
    temporary_name_for_rotation = "systemtemp"
    upgrade_settings { max_surge = "1" }
  }
  identity {
    type         = "UserAssigned"
    identity_ids = [var.control_plane.id]
  }
  kubelet_identity {
    client_id                 = var.kubelet.client_id
    object_id                 = var.kubelet.principal_id
    user_assigned_identity_id = var.kubelet.id
  }
  azure_active_directory_role_based_access_control {
    tenant_id              = var.tenant_id
    admin_group_object_ids = var.admin_group_object_ids
    azure_rbac_enabled     = true
  }
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_policy      = "calico"
    pod_cidr            = "10.244.0.0/16"
    service_cidr        = "10.43.0.0/16"
    dns_service_ip      = "10.43.0.10"
    outbound_type       = "loadBalancer"
    load_balancer_sku   = "standard"
  }
  tags = var.tags
}
