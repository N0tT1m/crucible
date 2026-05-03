[CmdletBinding()]
param(
  [ValidateSet("proxy","tun","wfp")][string]$Mode = "proxy"
)
$ErrorActionPreference = "Stop"

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
  Write-Error "must run elevated"; exit 1
}
$tor = Get-Command tor -ErrorAction SilentlyContinue
if (-not $tor) { Write-Error "tor missing (winget install TheTorProject.TorBrowser is too heavy; use 'scoop install tor')"; exit 1 }

$here = Split-Path -Parent $PSCommandPath
$root = Split-Path -Parent $here

# Save current state for rollback.
$state = @{
  ProxyEnable  = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings").ProxyEnable
  ProxyServer  = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue).ProxyServer
  Mode         = $Mode
  Time         = (Get-Date).ToString('o')
}
$state | ConvertTo-Json | Set-Content "$env:ProgramData\anonsurf-win\state.json"

# Start Tor.
Start-Process -FilePath $tor.Path -ArgumentList "-f","$root\etc\torrc" -WindowStyle Hidden

switch ($Mode) {
  "proxy" {
    Set-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyEnable -Value 1
    Set-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyServer -Value "socks=127.0.0.1:9050"
    netsh interface ipv4 set dnsservers name="Wi-Fi" static 127.0.0.1 primary 2>$null
    netsh interface ipv4 set dnsservers name="Ethernet" static 127.0.0.1 primary 2>$null
    Write-Host "[anonsurf-win] proxy mode active. Apps that ignore system proxy will leak."
  }
  "tun" {
    & "$here\tun_router.ps1" up
  }
  "wfp" {
    # Kill-switch: deny all outbound, then allow only the Tor process.
    New-NetFirewallRule -DisplayName "anonsurf-win:deny-out" -Direction Outbound -Action Block -Enabled True | Out-Null
    New-NetFirewallRule -DisplayName "anonsurf-win:allow-tor" -Direction Outbound -Action Allow -Program $tor.Path -Enabled True | Out-Null
    Write-Host "[anonsurf-win] WFP kill-switch on. Pair with 'enable --mode proxy' or 'tun' for actual routing."
  }
}
