resource "azurerm_virtual_network" "this" {
  name                = "${var.name}-vnet"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = ["10.42.0.0/16"]
  tags                = var.tags
}
resource "azurerm_subnet" "aks" {
  name                 = "aks"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.42.0.0/22"]
}
resource "azurerm_subnet" "private_endpoints" {
  name                 = "private-endpoints"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.42.4.0/24"]
}
resource "azurerm_network_security_group" "nodes" {
  name                = "${var.name}-nodes-nsg"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}
resource "azurerm_subnet_network_security_group_association" "nodes" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.nodes.id
}
