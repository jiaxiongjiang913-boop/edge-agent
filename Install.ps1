param(
    [string]$PythonPath,
    [ValidatePattern('^[a-p]{32}$')][string]$ExtensionId,
    [switch]$SkipDependencies,
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
. (Join-Path $PSScriptRoot 'Edge.ps1')
$edge = Get-EdgeExecutable
if (-not $edge) {
    Write-Host 'Microsoft Edge was not found. Install Edge before continuing.'
    Write-Host 'Official download: https://www.microsoft.com/edge/download'
    Write-Host 'Or run: powershell -NoProfile -ExecutionPolicy Bypass -File .\Download-Edge.ps1 -Install'
    throw 'Edge is missing. No browser was downloaded or installed automatically.'
}
Write-Host ('Using Microsoft Edge: ' + $edge)
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($PythonPath) {
        $bootstrapPython = (Get-Item -LiteralPath $PythonPath).FullName
    } else {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pythonCommand) { $bootstrapPython = $pythonCommand.Source }
        elseif ($pyCommand) { $bootstrapPython = $pyCommand.Source }
        else { throw 'Install Python 3.11 or newer, or pass -PythonPath.' }
    }
    & $bootstrapPython -B -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
    & $bootstrapPython -B -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
}
& $venvPython -B -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Recreate .venv with Python 3.11 or newer.' }
if (-not $SkipDependencies) {
    & $venvPython -B -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $venvPython -B -c 'import aiohttp; from mcp.server import MCPServer'
if ($LASTEXITCODE -ne 0) { throw 'Dependencies are missing. Run the installer without -SkipDependencies.' }
& $venvPython -B (Join-Path $PSScriptRoot 'agent_setup.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not generate local agent configuration.' }
if ($PrepareOnly) {
    Write-Host 'Environment ready. Load the unpacked extension, then rerun with -ExtensionId <ID>.'
    exit 0
}
Write-Host 'In Edge, open edge://extensions and enable Developer mode.'
Write-Host 'Load unpacked, select this folder:'
Write-Host (Join-Path $PSScriptRoot 'extension')
if (-not $ExtensionId) { $ExtensionId = (Read-Host 'Paste the 32-character Edge Agent extension ID').Trim() }
if ($ExtensionId -notmatch '^[a-p]{32}$') { throw 'Invalid extension ID.' }
& $venvPython -B (Join-Path $PSScriptRoot 'install_native_host.py') --extension-id $ExtensionId
if ($LASTEXITCODE -ne 0) { throw 'Native host registration failed.' }
Write-Host 'Installed. Click the Edge Agent toolbar icon to connect.'
Write-Host 'Universal MCP config: runtime\mcp-config.local.json. Merge into your agent client settings.'
Write-Host 'Optional Codex skill: run .venv\Scripts\python.exe -B install_skill.py --destination <skills-directory>'
