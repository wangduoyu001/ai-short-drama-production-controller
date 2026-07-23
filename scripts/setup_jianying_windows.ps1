param(
    [string]$Config = "script_mixer.local.json",
    [switch]$InstallMissingTools
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "[1/6] Installing Python project and Jianying draft adapter..."
python -m pip install --upgrade pip
python -m pip install -e ".[jianying]"

if (-not (Test-Path $Config)) {
    Write-Host "[2/6] Creating local config: $Config"
    script-driven-mixer init-config --out $Config
} else {
    Write-Host "[2/6] Reusing local config: $Config"
}

if ($InstallMissingTools -and -not (Test-CommandExists "ffmpeg")) {
    if (Test-CommandExists "winget") {
        Write-Host "[3/6] Installing FFmpeg with winget..."
        winget install --id Gyan.FFmpeg --exact --accept-package-agreements --accept-source-agreements
    } else {
        Write-Warning "winget is unavailable. Install a full FFmpeg build manually and rerun this script."
    }
} else {
    Write-Host "[3/6] FFmpeg automatic installation was not requested or FFmpeg already exists."
}

Write-Host "[4/6] Initializing local database..."
script-driven-mixer --config $Config init-db

Write-Host "[5/6] Checking local environment..."
script-driven-mixer --config $Config doctor

Write-Host "[6/6] Checking Jianying draft support..."
$JianyingExit = 0
script-driven-mixer --config $Config jianying-status
$JianyingExit = $LASTEXITCODE

Write-Host ""
Write-Host "Setup finished."
Write-Host "Next command:"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 -MediaRoot 'D:\素材' -Script 'input.txt' -Voice 'voice.wav'"
if ($JianyingExit -ne 0) {
    Write-Warning "The standard editable package is ready, but Jianying draft root was not detected. Set edit_package.jianying_draft_root in $Config or pass -DraftRoot when running."
}
