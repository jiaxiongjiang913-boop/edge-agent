$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Install.cmd first.' }
$launcherPath = Join-Path $PSScriptRoot 'launch.py'
Start-Process -FilePath $python -ArgumentList @('-B', ('"' + $launcherPath + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
