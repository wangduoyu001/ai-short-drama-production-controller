param(
    [string]$Owner = "wangduoyu001",
    [string]$RepoName = "video-Mixed-clip",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public",
    [string]$Target = "",
    [switch]$Force,
    [switch]$SkipTests,
    [switch]$UseExistingRemote
)

$ErrorActionPreference = "Stop"
$SourceRoot = Split-Path -Parent $PSScriptRoot
Set-Location $SourceRoot

if (-not $Target) {
    $Parent = Split-Path -Parent $SourceRoot
    $Target = Join-Path $Parent $RepoName
}
$Target = [System.IO.Path]::GetFullPath($Target)
$FullRepo = "$Owner/$RepoName"

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "[1/8] Checking source repository..."
if (-not (Test-Path (Join-Path $SourceRoot "short_drama_controller/script_mixer"))) {
    throw "Mixer source package was not found in: $SourceRoot"
}

Write-Host "[2/8] Building standalone repository at: $Target"
$BuildArgs = @(
    "scripts/build_standalone_mixer_repo.py",
    "--source", $SourceRoot,
    "--target", $Target
)
if ($Force) {
    $BuildArgs += "--force"
}
python @BuildArgs

Write-Host "[3/8] Creating isolated Python environment..."
Set-Location $Target
python -m venv .venv
$Python = Join-Path $Target ".venv/Scripts/python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment Python was not created: $Python"
}
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"

if (-not $SkipTests) {
    Write-Host "[4/8] Running standalone tests..."
    & $Python -m pytest -q
    & $Python -m ai_local_video_mixer.cli --help | Out-Null
} else {
    Write-Host "[4/8] Tests skipped by explicit request."
}

Write-Host "[5/8] Checking GitHub CLI..."
if (-not (Test-CommandExists "gh")) {
    if (Test-CommandExists "winget") {
        winget install --id GitHub.cli --exact --accept-package-agreements --accept-source-agreements
        $MachinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$MachinePath;$UserPath"
    }
}
if (-not (Test-CommandExists "gh")) {
    throw "GitHub CLI is unavailable. Install it with: winget install --id GitHub.cli --exact"
}

Write-Host "[6/8] Checking GitHub login..."
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub login is required. A browser login will open."
    & gh auth login --web --git-protocol https
}
& gh auth status

$UserJson = & gh api user
$User = $UserJson | ConvertFrom-Json
if (-not $User.login) {
    throw "Unable to read the authenticated GitHub user."
}
if ($Owner -eq "") {
    $Owner = $User.login
    $FullRepo = "$Owner/$RepoName"
}

Write-Host "[7/8] Initializing Git repository..."
if (Test-Path ".git") {
    Remove-Item -Recurse -Force ".git"
}
git init -b main
if (-not (git config user.name)) {
    git config user.name $User.login
}
if (-not (git config user.email)) {
    git config user.email "$($User.id)+$($User.login)@users.noreply.github.com"
}
git add .
git commit -m "Initial standalone local video mixer release"

Write-Host "[8/8] Creating and pushing GitHub repository: $FullRepo"
& gh repo view $FullRepo *> $null
$RemoteExists = $LASTEXITCODE -eq 0
if ($RemoteExists) {
    if (-not $UseExistingRemote) {
        throw "Remote repository already exists: https://github.com/$FullRepo . Re-run with -UseExistingRemote only if it is the intended empty repository."
    }
    git remote add origin "https://github.com/$FullRepo.git"
    git push -u origin main
} else {
    $VisibilityFlag = if ($Visibility -eq "private") { "--private" } else { "--public" }
    & gh repo create $FullRepo `
        $VisibilityFlag `
        --description "AI本地视频素材混剪：文案驱动自动粗剪、字幕对齐与剪映可编辑工程" `
        --source $Target `
        --remote origin `
        --push
}

Write-Host ""
Write-Host "Standalone repository created successfully."
Write-Host "Local path: $Target"
Write-Host "GitHub: https://github.com/$FullRepo"
Write-Host "Clone: git clone https://github.com/$FullRepo.git"
