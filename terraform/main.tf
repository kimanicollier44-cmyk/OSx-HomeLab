# OSx-HomeLab — OpenTofu / Terraform (blueprint, verbatim provider versions)
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    proxmox = { source = "bpg/proxmox", version = "~> 0.59.0" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.31.0" }
  }
}
provider "proxmox" {
  endpoint = "https://10.1.10.10:8006/api2/json"
  api_token = var.proxmox_api_token
  insecure = true
}
resource "proxmox_virtual_environment_download_file" "talos_image" {
  node_name = "superserver"
  content_type = "iso"
  datastore_id = "local"
  file_name = "talos-v1.8.0-proxmox-amd64.img"
  url = "https://factory.talos.dev/image/v1.8.0/amd64/proxmox.img"
}
resource "proxmox_virtual_environment_vm" "k8s_control_plane" {
  count = 3
  node_name = "superserver"
  name = "k8s-cp-0${count.index + 1}"
  tags = ["kubernetes", "control-plane", "talos"]
  machine = "q35"
  bios = "ovmf"
  cpu { cores = 4, sockets = 1, type = "host" }
  memory { dedicated = 8192 }
  disk { datastore_id = "local-lvm", file_id = proxmox_virtual_environment_download_file.talos_image.id, interface = "virtio0", size = 50 }
}
# Dedicated OSx microkernel test VM
resource "proxmox_virtual_environment_vm" "osx_node" {
  node_name = "superserver"
  name = "osx-custom-microkernel-node"
  tags = ["osx", "microkernel", "test"]
  machine = "q35"
  bios = "ovmf"
  cpu { cores = 2, sockets = 1, type = "host" }
  memory { dedicated = 4096 }
}
# One namespace per engine in the registry (osx-mesh, cognitive-mesh, ...)
resource "kubernetes_namespace" "meshes" {
  for_each = toset(["osx-mesh", "cognitive-mesh", "agents-xcrops-mesh", "quantum-trader-mesh", "autonomous-rnd-mesh", "advanced-medical-mesh", "crypto-forensics-mesh", "creator-pipeline-mesh", "sysadmin-mask-mesh"])
  metadata { name = each.value }
}
