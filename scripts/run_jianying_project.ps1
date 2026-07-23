param(
    [Parameter(Mandatory = $true)]
    [string]$MediaRoot,

    [Parameter(Mandatory = $true)]
    [string]$Script,

    [string]$Voice = "",
    [string]$Config = "script_mixer.local.json",
    [string]$DraftRoot = "",
    [string]$ProjectId = "",
    [int]$CandidateCount = 3,
    [double]$HandleBefore = 1.0,
    [double]$HandleAfter = 1.0,
    [switch]$FastScan,
    [switch]$SkipModels,
    [switch]$NoDraft,
    [switch]$RequireDraft,
    [switch]$NoPreview,
    [switch]$BurnSubtitles
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path $Config)) {
    throw "Local config not found: $Config. Run scripts/setup_jianying_windows.ps1 first."
}
if (-not (Test-Path $MediaRoot)) {
    throw "Media root not found: $MediaRoot"
}
if (-not (Test-Path $Script)) {
    throw "Script file not found: $Script"
}
if ($Voice -and -not (Test-Path $Voice)) {
    throw "Voice file not found: $Voice"
}

$Arguments = @(
    "--config", $Config,
    "make-jianying-project",
    "--media-root", $MediaRoot,
    "--script", $Script,
    "--candidate-count", "$CandidateCount",
    "--handle-before", "$HandleBefore",
    "--handle-after", "$HandleAfter"
)

if ($Voice) {
    $Arguments += @("--voice", $Voice, "--audio-mode", "mixed")
} else {
    $Arguments += @("--audio-mode", "source")
}
if ($DraftRoot) {
    $Arguments += @("--draft-root", $DraftRoot)
}
if ($ProjectId) {
    $Arguments += @("--project-id", $ProjectId)
}
if ($FastScan) {
    $Arguments += "--fast-scan"
}
if ($SkipModels) {
    $Arguments += @("--skip-enrich", "--skip-embeddings")
}
if ($NoDraft) {
    $Arguments += "--no-draft"
}
if ($RequireDraft) {
    $Arguments += "--require-draft"
}
if ($NoPreview) {
    $Arguments += "--no-preview"
}
if ($BurnSubtitles) {
    $Arguments += "--burn-subtitles"
}

Write-Host "Running script-driven-mixer with Jianying editable output..."
& script-driven-mixer @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Jianying project generation failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Completed. Check outputs/script_mixer/<project_id>/exports/jianying_package"
