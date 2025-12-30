Param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"

Write-Host "RetailOS Local Run (Windows)" -ForegroundColor Cyan
Write-Host "API  : http://127.0.0.1:$ApiPort" -ForegroundColor Gray
Write-Host "Web  : http://127.0.0.1:$WebPort" -ForegroundColor Gray
Write-Host ""

function Require-Command([string]$name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "Missing required command: $name" }
}

Require-Command "python"
Require-Command "npm"

# Simple env sanity (prints only booleans; no secrets)
$hasTm = ($env:CONSUMER_KEY -and $env:CONSUMER_SECRET -and $env:ACCESS_TOKEN -and $env:ACCESS_TOKEN_SECRET)
$hasGemini = [bool]$env:GEMINI_API_KEY
$hasOpenAI = [bool]$env:OPENAI_API_KEY
Write-Host ("Trade Me configured: " + $hasTm) -ForegroundColor Gray
Write-Host ("LLM configured (Gemini/OpenAI): " + ($hasGemini -or $hasOpenAI)) -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path ".venv")) {
  Write-Host "Creating venv..." -ForegroundColor Yellow
  python -m venv .venv
}

Write-Host "Starting API + Worker + Web in new windows..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  ".\\.venv\\Scripts\\activate; pip install -r requirements.txt; python -m uvicorn services.api.main:app --reload --port $ApiPort"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  ".\\.venv\\Scripts\\activate; python -u retail_os\\trademe\\worker.py"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd services\\web; npm install; npm run dev -- -p $WebPort"
) -WindowStyle Normal

Write-Host ""
Write-Host "Done. Use Ops Workbench → Runbook." -ForegroundColor Green

