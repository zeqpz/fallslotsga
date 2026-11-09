# Prints where the Claude Code CLI really lives for a normal (non-app) shell.
$cands = @()
$cands += Get-ChildItem "$env:APPDATA\Claude\claude-code" -Recurse -Filter claude.exe -ErrorAction SilentlyContinue
$cands += Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -Filter "Claude*" -ErrorAction SilentlyContinue |
  ForEach-Object { Get-ChildItem (Join-Path $_.FullName "LocalCache\Roaming\Claude\claude-code") -Recurse -Filter claude.exe -ErrorAction SilentlyContinue }
$cands += Get-Command claude -ErrorAction SilentlyContinue | ForEach-Object { Get-Item $_.Source }
$cands | Sort-Object LastWriteTime -Descending | Select-Object -ExpandProperty FullName
