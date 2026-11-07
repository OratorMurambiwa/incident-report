variable "name" {
  type        = string
  description = "Resource name or prefix."
}
variable "location" {
  type        = string
  description = "Azure region."
}
variable "resource_group_name" {
  type        = string
  description = "Owning resource group."
}
variable "tags" {
  type        = map(string)
  description = "Nonsecret tags."
}
