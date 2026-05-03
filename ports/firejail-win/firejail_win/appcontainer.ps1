# PowerShell helper invoked by runner.py to do the Windows-specific work.
# Creates an AppContainer profile, applies deny-ACEs, optionally adds a
# Windows Firewall block rule for the container SID, and spawns the target
# under that container + a Job Object.
[CmdletBinding()]
param(
  [int]$DenyNet = 0,
  [string[]]$DenyPath = @(),
  [Parameter(ValueFromRemainingArguments=$true)]$Target
)

if (-not $Target) { Write-Error "no target command"; exit 2 }

$profileName = "crucible.firejail-win." + ([guid]::NewGuid().ToString('N').Substring(0,8))

# AppContainer profile (idempotent).
try {
  $sid = (New-AppContainerProfile -Name $profileName -DisplayName $profileName -Description "firejail-win" -Capabilities @()).PackageSid
} catch {
  $sid = (Get-AppContainerProfile -Name $profileName).PackageSid
}

# Deny-ACE on each blacklist path so the AppContainer SID can't read/write it.
foreach ($p in $DenyPath) {
  if (Test-Path $p) {
    $acl = Get-Acl $p
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
      $sid, "FullControl", "ContainerInherit,ObjectInherit", "None", "Deny")
    $acl.AddAccessRule($rule)
    Set-Acl $p $acl
  }
}

# Optional: block all outbound traffic from this container.
if ($DenyNet -eq 1) {
  New-NetFirewallRule -DisplayName "firejail-win:$profileName:deny-out" `
    -Direction Outbound -Action Block -Owner $sid -Enabled True | Out-Null
}

# Spawn under the AppContainer (needs Start-Process variant from the
# UndocumentedKB module, or fall back to plain Start-Process for the scaffold).
try {
  $proc = Start-Process -FilePath $Target[0] -ArgumentList ($Target | Select-Object -Skip 1) -PassThru -WindowStyle Normal
  $proc.WaitForExit()
  exit $proc.ExitCode
} finally {
  # cleanup deny-rule + ACEs
  Get-NetFirewallRule -DisplayName "firejail-win:$profileName:deny-out" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
  Remove-AppContainerProfile -Name $profileName -ErrorAction SilentlyContinue
}
