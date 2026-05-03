$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSCommandPath
Write-Host "[firejail-win] dependencies are stdlib + (optional) pywin32."
Write-Host "[firejail-win] add to PATH: `$env:PATH += ';$here\bin'"
