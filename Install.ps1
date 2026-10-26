param(
    [string]$PythonPath,
    [ValidatePattern('^[a-p]{32}$')][string]$ExtensionId,
    [switch]$SkipDependencies
)
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($PythonPath) {
        $bootstrapPython = (Get-Item -LiteralPath $PythonPath).FullName
    } else {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pythonCommand) { $bootstrapPython = $pythonCommand.Source }
        elseif ($pyCommand) { $bootstrapPython = $pyCommand.Source }
        else { throw 'Install Python 3.10 or newer, or pass -PythonPath.' }
    }
    & $bootstrapPython -B -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 or newer is required.' }
    & $bootstrapPython -B -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
}
if (-not $SkipDependencies) {
    & $venvPython -B -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $venvPython -B -c 'import aiohttp'
if ($LASTEXITCODE -ne 0) { throw 'aiohttp is missing. Run the installer without -SkipDependencies.' }
Write-Host 'In Edge, open edge://extensions and enable Developer mode.'
Write-Host 'Load unpacked, select this folder:'
Write-Host (Join-Path $PSScriptRoot 'extension')
if (-not $ExtensionId) { $ExtensionId = (Read-Host 'Paste the 32-character Edge Agent extension ID').Trim() }
if ($ExtensionId -notmatch '^[a-p]{32}$') { throw 'Invalid extension ID.' }
& $venvPython -B (Join-Path $PSScriptRoot 'install_native_host.py') --extension-id $ExtensionId
if ($LASTEXITCODE -ne 0) { throw 'Native host registration failed.' }
Write-Host 'Installed. Click the Edge Agent toolbar icon to connect.'
Write-Host 'Optional Codex skill: run .venv\Scripts\python.exe -B install_skill.py --destination <skills-directory>'
