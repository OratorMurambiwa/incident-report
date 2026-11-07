resource "azurerm_user_assigned_identity" "this" {
  for_each            = toset(["control-plane", "kubelet", "workload"])
  name                = "${var.name}-${each.key}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}
