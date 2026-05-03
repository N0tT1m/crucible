#!/usr/bin/env bash
set -euo pipefail
VM="${CRUCIBLE_LIMA_VM:-aircrack}"

cmd="${1:-}"; shift || true
case "$cmd" in
  up)
    if ! limactl list -q | grep -qx "$VM"; then
      limactl start --name "$VM" --tty=false template://default <<'YAML'
images:
- location: "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img"
  arch: "aarch64"
- location: "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
  arch: "x86_64"
mounts:
- location: "~"
  writable: false
provision:
- mode: system
  script: |
    #!/bin/bash
    set -eux
    apt-get update
    apt-get install -y aircrack-ng iw usbutils linux-modules-extra-$(uname -r)
YAML
    else
      limactl start "$VM"
    fi
    echo "[inject] VM '$VM' is running. Use 'inject pass <busid>' to attach a USB radio."
    ;;
  down)   limactl stop "$VM" ;;
  shell)  exec limactl shell "$VM" ;;
  pass)
    busid="${1:?usage: inject pass <busid>}"
    echo "[inject] attaching USB device $busid → $VM"
    # Lima's vz driver supports usb-device on macOS hosts. Edit the VM yaml at
    # ~/.lima/$VM/lima.yaml and add:
    #   networks: [{lima: shared}]
    #   usb: [{vendorId: 0x0bda, productId: 0x8812}]
    # then restart: limactl stop $VM && limactl start $VM
    echo "Edit ~/.lima/$VM/lima.yaml: add a 'usb' entry with the device's vendor/product IDs."
    echo "Then: limactl stop $VM && limactl start $VM"
    ;;
  *) echo "usage: inject <up|down|shell|pass>"; exit 2 ;;
esac
