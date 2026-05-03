# aircrack-win — native sniff/crack on Windows + WSL2 bridge for active attacks.
[CmdletBinding()]
param(
  [Parameter(Position=0)][string]$Cmd = "help",
  [Parameter(ValueFromRemainingArguments=$true)]$Rest
)
$here = Split-Path -Parent $PSCommandPath
$lib  = Join-Path (Split-Path -Parent $here) "lib"

switch ($Cmd) {
  "scan"     { & "$lib\scan.ps1" @Rest }
  "sniff"    { & "$lib\sniff.ps1" @Rest }
  "crack"    { & "$lib\crack.ps1" @Rest }
  "wordlist" { & "$lib\wordlist.ps1" @Rest }
  "inject"   { & "$lib\wsl_inject.ps1" @Rest }
  "doctor" {
    @(
      @{ name="aircrack-ng"; cmd="aircrack-ng" },
      @{ name="dumpcap";     cmd="dumpcap" },
      @{ name="usbipd";      cmd="usbipd" },
      @{ name="wsl";         cmd="wsl" }
    ) | ForEach-Object {
      $found = Get-Command $_.cmd -ErrorAction SilentlyContinue
      "{0,-12} {1}" -f $_.name, ($(if ($found) {"ok"} else {"missing"}))
    }
  }
  default {
@"
aircrack-win — Windows-native Wi-Fi recon + cracking, WSL2 bridge for injection.

usage: aircrack-win <scan|sniff|crack|wordlist|inject|doctor> [args...]

  scan                          Survey nearby networks (netsh wlan).
  sniff <iface> <ch> [out.pcap] Passive capture via Npcap dumpcap.
  crack <pcap> <wordlist>       Offline WPA/WEP recovery (aircrack-ng.exe).
  wordlist <rockyou|crunch>     Generate or fetch a wordlist.
  inject <up|attach|shell>      Manage WSL2 + usbipd-win for active attacks.
  doctor                        Check dependencies.
"@
  }
}
