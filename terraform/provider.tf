terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Dummy provider block (NO subscription, NO service principal)
provider "azurerm" {
  features {}
}
