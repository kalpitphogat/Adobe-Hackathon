# Rehearse REPLAY_IT_Professionals.txt verbatim, headless, from a fresh unzip.
#
# Takes the step-2 prompt straight out of the REPLAY file (so a rehearsal can never drift
# from what judges will paste), unzips round3-frozen/submission.zip into a new folder under
# runs/, activates the given venv, runs Claude Code with -p, and saves the agent's answer
# to rehearsal/<date>_<label>.md.
#
# Usage (from the repo root):
#   powershell -File tools\rehearse.ps1 -Url https://www.ikea.com/ -Label ikea_opus
#   powershell -File tools\rehearse.ps1 -Url https://www.ikea.com/ -Label ikea_sonnet -Model claude-sonnet-5
#   powershell -File tools\rehearse.ps1 -Url https://www.ikea.com/ -Label ikea_norender -Venv .venv-norender
param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$Label,
    [string]$Model = "claude-opus-5-5",
    [string]$Venv = ".venv"
)
$ErrorActionPreference = "Stop"
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
$repo = Split-Path -Parent $PSScriptRoot

$prompt = (Get-Content "$repo\REPLAY_IT_Professionals.txt" -Encoding utf8 |
    Where-Object { $_ -match "SKILL\.md" -and $_.TrimEnd().EndsWith("URL: <URL>") } |
    Select-Object -First 1)
if (-not $prompt) { throw "step-2 prompt (ending 'URL: <URL>') not found in REPLAY" }
$prompt = $prompt.Trim().Replace("URL: <URL>", "URL: $Url")

$work = "$repo\runs\rehearse_$Label\brand-ai-readiness-audit"
if (Test-Path "$repo\runs\rehearse_$Label") { Remove-Item -Recurse -Force "$repo\runs\rehearse_$Label" }
New-Item -ItemType Directory $work | Out-Null
Expand-Archive "$repo\round3-frozen\submission.zip" $work
Set-Location $work
& "$repo\$Venv\Scripts\Activate.ps1"

$date = Get-Date -Format "yyyy-MM-dd"
$out = "$repo\rehearsal\${date}_$Label.md"
$pyver = (python --version) 2>&1
$pw = (python -c "import importlib.util as u; print('yes' if u.find_spec('playwright') else 'no')") 2>&1
$started = Get-Date
$answer = $prompt | claude -p --model $Model --allowedTools "Bash(python:*)" "Read" 2>&1 | Out-String
$code = $LASTEXITCODE
$secs = [int]((Get-Date) - $started).TotalSeconds
$report = Test-Path "audit-output\audit-report.json"

$header = @"
<!-- rehearsal: $Label | url: $Url | model: $Model | harness: $(claude --version) | python: $pyver | playwright: $pw | exit: $code | seconds: $secs | report written: $report -->

"@
[IO.File]::WriteAllText($out, $header + $answer, (New-Object Text.UTF8Encoding $false))
"rehearsal $Label -> exit $code, $secs s, report=$report, saved $out"
