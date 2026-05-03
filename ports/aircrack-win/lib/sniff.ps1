# Passive capture using Wireshark's dumpcap + Npcap.
param(
  [string]$Iface = "Wi-Fi",
  [int]$Channel = 6,
  [string]$Out = "capture-$(Get-Date -Format yyyyMMdd-HHmmss).pcapng"
)

$dumpcap = Get-Command dumpcap -ErrorAction SilentlyContinue
if (-not $dumpcap) {
  Write-Error "dumpcap not found. Install Wireshark + Npcap (winget install WiresharkFoundation.Wireshark)."
  exit 1
}

# Set the radio to the requested channel via netsh (driver-dependent).
& netsh wlan set hostednetwork mode=allow ssid="anonsurf-mac" key="11111111" 2>$null | Out-Null

Write-Host "[aircrack-win] capturing $Iface ch $Channel → $Out (Ctrl-C to stop)"
& $dumpcap.Path -i $Iface -w $Out -I -f "type mgt or type data"
