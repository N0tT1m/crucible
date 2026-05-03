[CmdletBinding()] param()
# NEWNYM via Tor's ControlPort. Cookie auth (per torrc).
$cookiePath = "$env:ProgramData\anonsurf-win\data\control_auth_cookie"
if (-not (Test-Path $cookiePath)) { Write-Error "no control cookie — is Tor running?"; exit 1 }
$cookieHex = -join ((Get-Content $cookiePath -Encoding Byte) | ForEach-Object { "{0:X2}" -f $_ })

$client = New-Object Net.Sockets.TcpClient("127.0.0.1", 9051)
$stream = $client.GetStream()
$writer = New-Object IO.StreamWriter($stream); $writer.AutoFlush = $true
$reader = New-Object IO.StreamReader($stream)

$writer.WriteLine("AUTHENTICATE $cookieHex")
$writer.WriteLine("SIGNAL NEWNYM")
$writer.WriteLine("QUIT")

while (-not $reader.EndOfStream) { $reader.ReadLine() }
$client.Close()

Write-Host "[anonsurf-win] new circuit requested."
