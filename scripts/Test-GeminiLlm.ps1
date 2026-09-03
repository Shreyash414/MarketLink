param(
    [string]$Prompt = 'What is MSP?',
    [string]$EnvironmentFile = '.env',
    [string]$Model = 'gemini-3.5-flash-lite',
    [string]$Endpoint = 'https://generativelanguage.googleapis.com/v1beta/interactions'
)

$ErrorActionPreference = 'Stop'

function Read-EnvironmentValue {
    param([string]$Path, [string]$Name)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $line = Get-Content -LiteralPath $Path |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -Last 1
    if ($null -eq $line) {
        return $null
    }
    return $line.Substring($line.IndexOf('=') + 1).Trim()
}

function Get-SafeProviderError {
    param([string]$ErrorJson, [string]$Credential)

    if ([string]::IsNullOrWhiteSpace($ErrorJson)) {
        return 'providerStatus=unavailable providerCode=unavailable providerMessage=unavailable'
    }
    try {
        $providerError = ($ErrorJson | ConvertFrom-Json).error
        $message = [string]$providerError.message
        if (-not [string]::IsNullOrEmpty($Credential)) {
            $message = $message.Replace($Credential, '[REDACTED_CREDENTIAL]')
        }
        $message = $message -replace '(?i)(key|token|authorization|credential)\s*[=:]\s*\S+', '$1=[REDACTED]'
        $message = $message -replace 'https?://\S+', '[REDACTED_URL]'
        if ($message.Length -gt 300) {
            $message = $message.Substring(0, 300)
        }
        return "providerStatus=$($providerError.status) providerCode=$($providerError.code) providerMessage=$message"
    } catch {
        return 'providerStatus=unparseable providerCode=unparseable providerMessage=unavailable'
    }
}

$apiKey = [Environment]::GetEnvironmentVariable('GEMINI_LLM_API_KEY')
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY')
}
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = Read-EnvironmentValue -Path $EnvironmentFile -Name 'GEMINI_LLM_API_KEY'
}
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = Read-EnvironmentValue -Path $EnvironmentFile -Name 'GEMINI_API_KEY'
}
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw 'No Gemini API key is available in the environment or the selected environment file.'
}

$request = @{
    model = $Model
    system_instruction = 'Answer as an agriculture assistant for Indian farmers in at most three short plain sentences. Do not use Markdown or invent live market data.'
    input = @(
        @{
            type = 'user_input'
            content = @(@{ type = 'text'; text = $Prompt })
        }
    )
    store = $false
    generation_config = @{ max_output_tokens = 96; thinking_level = 'minimal' }
} | ConvertTo-Json -Depth 8 -Compress

$timer = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $response = Invoke-WebRequest `
        -Uri $Endpoint `
        -Method Post `
        -Headers @{ 'x-goog-api-key' = $apiKey } `
        -ContentType 'application/json' `
        -Body $request `
        -TimeoutSec 15
} catch {
    $statusCode = if ($null -ne $_.Exception.Response) {
        [int]$_.Exception.Response.StatusCode
    } else {
        'unavailable'
    }
    $safeProviderError = Get-SafeProviderError -ErrorJson $_.ErrorDetails.Message -Credential $apiKey
    throw "Gemini LLM smoke test failed. exceptionClass=$($_.Exception.GetType().FullName) httpStatus=$statusCode $safeProviderError"
} finally {
    $timer.Stop()
    $apiKey = $null
}

$document = $response.Content | ConvertFrom-Json
$parts = @($document.steps |
    Where-Object { $_.type -eq 'model_output' } |
    ForEach-Object { $_.content } |
    Where-Object { $_.type -eq 'text' -and -not [string]::IsNullOrWhiteSpace($_.text) } |
    ForEach-Object { $_.text })
$answer = ($parts -join '').Trim()
if ([string]::IsNullOrWhiteSpace($answer)) {
    throw "Gemini LLM smoke test returned no model text. httpStatus=$([int]$response.StatusCode)"
}

Write-Host 'Gemini LLM smoke test: PASS' -ForegroundColor Green
Write-Host "HTTP status: $([int]$response.StatusCode)"
Write-Host "Model: $Model"
Write-Host "Latency ms: $($timer.ElapsedMilliseconds)"
Write-Host "Response characters: $($answer.Length)"
Write-Host "Assistant response: $answer"
