[CmdletBinding()] param()
$ErrorActionPreference = "Stop"

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
  Write-Error "must run elevated"; exit 1
}

$statePath = "$env:ProgramData\anonsurf-win\state.json"
if (-not (Test-Path $statePath)) { Write-Host "no active session"; return }
$state = Get-Content $statePath | ConvertFrom-Json

# Stop tor.
Get-Process tor -ErrorAction SilentlyContinue | Where-Object { $_.MainModule.FileName -like "*\anonsurf-win*" -or $true } | Stop-Process -Force -ErrorAction SilentlyContinue

switch ($state.Mode) {
  "proxy" {
    Set-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyEnable -Value $state.ProxyEnable
    if ($state.ProxyServer) {
      Set-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyServer -Value $state.ProxyServer
    }
    netsh interface ipv4 set dnsservers name="Wi-Fi" dhcp 2>$null
    netsh interface ipv4 set dnsservers name="Ethernet" dhcp 2>$null
  }
  "tun" {
    $here = Split-Path -Parent $PSCommandPath
    & "$here\tun_router.ps1" down
  }
  "wfp" {
    Get-NetFirewallRule -DisplayName "anonsurf-win:deny-out","anonsurf-win:allow-tor" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
  }
}

Remove-Item $statePath -Force
ipconfig /flushdns | Out-Null
Write-Host "[anonsurf-win] disabled."
