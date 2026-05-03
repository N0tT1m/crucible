param(
  [string]$Kind = "help",
  [Parameter(ValueFromRemainingArguments=$true)]$Rest
)
switch ($Kind) {
  "rockyou" {
    $out = if ($Rest) { $Rest[0] } else { ".\rockyou.txt" }
    if (Test-Path $out) { "$out exists"; return }
    Invoke-WebRequest -Uri "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt" -OutFile $out
  }
  "crunch" {
    $cmd = Get-Command crunch -ErrorAction SilentlyContinue
    if (-not $cmd) { Write-Error "crunch missing (scoop install crunch)"; exit 1 }
    & $cmd.Path @Rest
  }
  default { "usage: wordlist <rockyou [path] | crunch ...>" }
}
