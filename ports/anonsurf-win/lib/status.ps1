[CmdletBinding()] param()

$tor = Get-Process tor -ErrorAction SilentlyContinue
"tor:    {0}" -f ($(if ($tor) {"running (pid $($tor.Id))"} else {"stopped"}))

$proxy = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings"
"proxy:  enable={0} server={1}" -f $proxy.ProxyEnable, $proxy.ProxyServer

$dns = (Get-DnsClientServerAddress | Where-Object {$_.AddressFamily -eq 2 -and $_.ServerAddresses}).ServerAddresses -join ","
"dns:    $dns"

try {
  $ip = (Invoke-RestMethod "https://check.torproject.org/api/ip" -TimeoutSec 5)
  "egress: {0} (Tor={1})" -f $ip.IP, $ip.IsTor
} catch {
  "egress: (check.torproject.org unreachable)"
}
