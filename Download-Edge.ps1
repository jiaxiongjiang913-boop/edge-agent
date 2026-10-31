param([switch]$Install)
$ErrorActionPreference = 'Stop'
$downloadDirectory = Join-Path $PSScriptRoot 'downloads'
New-Item -ItemType Directory -Path $downloadDirectory -Force | Out-Null
$installer = Join-Path $downloadDirectory 'MicrosoftEdgeSetup.exe'
$url = 'https://go.microsoft.com/fwlink/?linkid=2109047&Channel=Stable&language=en'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Write-Host 'Downloading the official Microsoft Edge installer...'
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $installer
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
    throw 'The installer does not have a valid Microsoft signature. Do not run it.'
}
Write-Host ('Downloaded and verified: ' + $installer)
if ($Install) {
    Start-Process -FilePath $installer -Wait
    Write-Host 'After Edge finishes installing, run Install.cmd again.'
}
