# aircrack-win install — winget for tools, manual hint for Npcap.
$ErrorActionPreference = "Stop"

function Have($exe) { [bool](Get-Command $exe -ErrorAction SilentlyContinue) }

if (-not (Have "winget")) {
  Write-Error "winget required. Install App Installer from the Microsoft Store."
  exit 1
}

if (-not (Have "aircrack-ng")) { winget install -e --id Aircrack-ng.Aircrack-ng }
if (-not (Have "dumpcap"))     { winget install -e --id WiresharkFoundation.Wireshark }
if (-not (Have "usbipd"))      { winget install -e --id dorssel.usbipd-win }
if (-not (Have "wsl"))         { wsl --install -d Ubuntu }

Write-Host "[aircrack-win] installed. Run: aircrack-win doctor"
