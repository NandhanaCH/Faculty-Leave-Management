# SAMPLE Infrastructure-as-Code for documentation only

resource "azurerm_resource_group" "rg" {
  name     = "facultyLeaveRG"
  location = "southindia"
}

resource "azurerm_container_registry" "acr" {
  name                = "facultyleaveacr123"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_app_service_plan" "plan" {
  name                = "FacultyLeavePlan"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "Basic"
    size = "B1"
  }
}

resource "azurerm_linux_web_app" "webapp" {
  name                = "faculty-leave-plan"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  service_plan_id     = azurerm_app_service_plan.plan.id

  site_config {
    linux_fx_version = "DOCKER|facultyleaveacr123.azurecr.io/faculty-leave-app:latest"
  }
}
