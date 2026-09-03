param(
    [string]$LocalUrl = 'http://localhost:8080',
    [string]$WebSocketPath = '/media'
)

if (-not $WebSocketPath.StartsWith('/')) {
    throw 'WebSocketPath must start with a forward slash.'
}

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($null -eq $cloudflared) {
    throw @'
cloudflared is not installed or is not available on PATH.
Install it with:
  winget install --id Cloudflare.cloudflared --exact
Then open a new terminal and run this script again.
'@
}

$configCandidates = @(
    (Join-Path $env:USERPROFILE '.cloudflared\config.yml'),
    (Join-Path $env:USERPROFILE '.cloudflared\config.yaml')
)
if ($configCandidates | Where-Object { Test-Path -LiteralPath $_ }) {
    Write-Warning 'Cloudflare Quick Tunnels may not start while a .cloudflared config.yml/config.yaml file exists.'
}

Write-Output "Starting a development-only Cloudflare Quick Tunnel for $LocalUrl"
Write-Output 'Keep this terminal open. Stop the tunnel with Ctrl+C.'

$publicUrlShown = $false
$publicUrlPattern = 'https://[a-z0-9-]+\.trycloudflare\.com'

& $cloudflared.Source tunnel --url $LocalUrl 2>&1 | ForEach-Object {
    $line = $_.ToString()
    Write-Host $line

    if (-not $publicUrlShown -and $line -match $publicUrlPattern) {
        $httpsUrl = $Matches[0]
        $wssUrl = $httpsUrl -replace '^https://', 'wss://'
        Write-Host ''
        Write-Host "Public health URL: $httpsUrl/health" -ForegroundColor Green
        Write-Host "Public WebSocket URL: $wssUrl$WebSocketPath" -ForegroundColor Green
        Write-Host "Test command: .\scripts\Test-MediaWebSocket.ps1 -Uri '$wssUrl$WebSocketPath'" -ForegroundColor Green
        Write-Host ''
        $publicUrlShown = $true
    }
}

exit $LASTEXITCODE
