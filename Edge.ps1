function Get-EdgeExecutable {
    $candidates = @()
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
        if ($base) { $candidates += Join-Path $base 'Microsoft\Edge\Application\msedge.exe' }
    }
    $command = Get-Command msedge.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($path in $candidates) { if (Test-Path -LiteralPath $path -PathType Leaf) { return $path } }
    return $null
}
