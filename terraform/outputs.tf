output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "webapp_url" {
  value = "https://${azurerm_linux_web_app.webapp.name}.azurewebsites.net"
}
