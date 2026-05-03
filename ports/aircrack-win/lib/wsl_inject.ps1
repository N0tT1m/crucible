# WSL2 + usbipd-win bridge for live frame injection.
param(
  [string]$Cmd = "help",
  [Parameter(ValueFromRemainingArguments=$true)]$Rest
)

function Need($exe, $hint) {
  if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
    Write-Error "$exe not found. $hint"; exit 1
  }
}

switch ($Cmd) {
  "up" {
    Need "wsl"   "Install WSL: 'wsl --install -d Ubuntu' (admin shell)"
    Need "usbipd" "Install usbipd-win: 'winget install usbipd'"
    Write-Host "[inject] ensuring Ubuntu has aircrack-ng + drivers..."
    wsl -d Ubuntu -- bash -c "sudo apt-get update && sudo apt-get install -y aircrack-ng iw usbutils linux-modules-extra-`$(uname -r)`"
  }
  "list" { usbipd list }
  "attach" {
    if (-not $Rest) { Write-Error "usage: inject attach <busid>"; exit 2 }
    $busid = $Rest[0]
    Write-Host "[inject] binding + attaching $busid to WSL..."
    usbipd bind --busid $busid
    usbipd attach --wsl --busid $busid
  }
  "shell" { wsl -d Ubuntu }
  default {
@"
inject <subcommand> ...
  up                    Provision WSL Ubuntu with aircrack-ng + drivers.
  list                  List USB devices visible to usbipd.
  attach <busid>        Bind + attach a USB radio into WSL.
  shell                 Drop into the WSL Ubuntu shell.
"@
  }
}
