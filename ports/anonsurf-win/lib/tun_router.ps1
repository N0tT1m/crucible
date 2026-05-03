[CmdletBinding()] param([string]$Cmd = "up")
# Wintun-backed TUN router. Requires Wintun driver (https://www.wintun.net/).
# This is a scaffold — the real implementation is a small Go or Rust binary
# that opens a Wintun adapter, reads IP packets, and forwards each TCP
# connection through the Tor SOCKS proxy at 127.0.0.1:9050.
#
# Reference designs:
#   - WireGuard-Windows (uses Wintun the same way)
#   - OnionFruit Connect (closed source, demonstrates the model)
#   - tun2socks (Go) — drop-in for the userspace half

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSCommandPath
$bin  = Join-Path (Split-Path -Parent $here) "bin"

switch ($Cmd) {
  "up" {
    $t2s = Join-Path $bin "tun2socks.exe"
    if (-not (Test-Path $t2s)) {
      Write-Warning "tun2socks.exe not bundled. Download from https://github.com/xjasonlyu/tun2socks/releases"
      Write-Warning "and drop into ports\anonsurf-win\bin\."
      exit 1
    }
    Start-Process -FilePath $t2s -ArgumentList "-device wintun://anonsurf -proxy socks5://127.0.0.1:9050 -loglevel warning" -WindowStyle Hidden
    # Add default route into the wintun adapter once it appears.
    Start-Sleep 2
    $iface = (Get-NetAdapter -Name "anonsurf" -ErrorAction SilentlyContinue).ifIndex
    if ($iface) {
      route add 0.0.0.0 mask 0.0.0.0 0.0.0.1 metric 1 if $iface | Out-Null
      Set-DnsClientServerAddress -InterfaceIndex $iface -ServerAddresses 127.0.0.1
    }
  }
  "down" {
    Get-Process tun2socks -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    route delete 0.0.0.0 mask 0.0.0.0 0.0.0.1 2>$null | Out-Null
  }
}
