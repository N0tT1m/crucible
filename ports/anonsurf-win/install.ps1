$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSCommandPath

if (-not (Get-Command tor -ErrorAction SilentlyContinue)) {
  if (Get-Command scoop -ErrorAction SilentlyContinue) { scoop install tor }
  else { Write-Warning "Install Tor manually (scoop install tor) or via the Tor Project release." }
}

New-Item -ItemType Directory -Force -Path "$env:ProgramData\anonsurf-win\data" | Out-Null
Write-Host "[anonsurf-win] installed. Add to PATH: `$env:PATH += ';$here\bin'"
Write-Host "[anonsurf-win] tun mode also needs Wintun + tun2socks.exe in bin\."
