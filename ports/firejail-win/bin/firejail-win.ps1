$here = Split-Path -Parent $PSCommandPath
$root = Split-Path -Parent $here
$env:PYTHONPATH = "$root;$env:PYTHONPATH"
& python -m firejail_win.cli @args
exit $LASTEXITCODE
