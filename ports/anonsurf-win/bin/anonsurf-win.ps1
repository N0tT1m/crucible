[CmdletBinding()]
param(
  [Parameter(Position=0)][string]$Cmd = "help",
  [Parameter(ValueFromRemainingArguments=$true)]$Rest
)
$here = Split-Path -Parent $PSCommandPath
$lib  = Join-Path (Split-Path -Parent $here) "lib"

switch ($Cmd) {
  "enable"   { & "$lib\enable.ps1"   @Rest }
  "disable"  { & "$lib\disable.ps1"  @Rest }
  "status"   { & "$lib\status.ps1"   @Rest }
  "changeid" { & "$lib\changeid.ps1" @Rest }
  default {
@"
anonsurf-win — force traffic through Tor on Windows.

  enable [--mode proxy|tun|wfp]    Start tor, install routing/firewall rules.
  disable                          Restore proxy/DNS, stop tor, drop rules.
  status                           Show tor process, proxy state, egress IP.
  changeid                         Request a new Tor circuit (NEWNYM).

Run elevated.
"@
  }
}
