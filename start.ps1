Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== GPThub Quick Start (Windows) ==="

function Ensure-Command {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Set-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $safeValue = $Value.Replace("'", "''")
    $line = "$Key='$safeValue'"
    $pattern = "(?m)^$([Regex]::Escape($Key))\s*=.*$"

    if ([Regex]::IsMatch($Content, $pattern)) {
        return [Regex]::Replace($Content, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $line })
    }

    if (-not $Content.EndsWith("`n")) {
        $Content += "`r`n"
    }

    return $Content + $line + "`r`n"
}

Ensure-Command -Name "docker"

docker compose version | Out-Null

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$envPath = Join-Path $repoRoot ".env"
$exampleEnvPath = Join-Path $repoRoot ".env.example"

if (-not (Test-Path $envPath)) {
    if (-not (Test-Path $exampleEnvPath)) {
        throw "ERROR: .env.example not found"
    }

    Copy-Item $exampleEnvPath $envPath

    $apiKey = Read-Host "Enter MWS API key"
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        throw "ERROR: API key is required"
    }

    $dotenv = Get-Content -Path $envPath -Raw -Encoding UTF8
    $keys = @(
        "MWS_API_KEY",
        "OPENAI_API_KEYS",
        "IMAGES_OPENAI_API_KEY",
        "AUDIO_STT_OPENAI_API_KEY",
        "RAG_OPENAI_API_KEY"
    )

    foreach ($key in $keys) {
        $dotenv = Set-DotEnvValue -Content $dotenv -Key $key -Value $apiKey
    }

    Set-Content -Path $envPath -Value $dotenv -Encoding UTF8
    Write-Host ".env created with your API key"
}

Write-Host ""
Write-Host "Starting GPThub (first build may take 5-10 min)..."
Write-Host "App will be available at http://localhost:3000"
Write-Host ""

docker compose up --build
