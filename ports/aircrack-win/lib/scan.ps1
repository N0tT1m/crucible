# BSSID-level survey via the built-in WLAN service.
$raw = & netsh wlan show networks mode=Bssid
$ssid = $null; $bssid = $null
$results = @()
foreach ($line in $raw) {
  if ($line -match '^\s*SSID\s+\d+\s*:\s*(.*)$') { $ssid  = $Matches[1] }
  if ($line -match '^\s*BSSID\s+\d+\s*:\s*(.+)$') { $bssid = $Matches[1] }
  if ($line -match '^\s*Signal\s*:\s*(\d+%)') {
    $results += [pscustomobject]@{ SSID=$ssid; BSSID=$bssid; Signal=$Matches[1] }
  }
}
$results | Sort-Object Signal -Descending | Format-Table -AutoSize
