# Offline WPA/WEP recovery via the bundled aircrack-ng.exe.
param(
  [Parameter(Mandatory=$true)][string]$Pcap,
  [Parameter(Mandatory=$true)][string]$Wordlist,
  [Parameter(ValueFromRemainingArguments=$true)]$Extra
)
$cmd = Get-Command aircrack-ng -ErrorAction SilentlyContinue
if (-not $cmd) {
  Write-Error "aircrack-ng not on PATH. Install via Scoop: scoop install aircrack-ng"
  exit 1
}
& $cmd.Path -w $Wordlist @Extra $Pcap
