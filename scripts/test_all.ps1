$ErrorActionPreference = "Stop"

Write-Host "=============================" -ForegroundColor Cyan
Write-Host "1. Running ALL pytest Tests" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) { 
    Write-Host "PYTEST FAILED" -ForegroundColor Red
    exit 1 
}

Write-Host "`n=============================" -ForegroundColor Cyan
Write-Host "2. Building Next.js Frontend" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Push-Location services/web
npm run build
$buildResult = $LASTEXITCODE
Pop-Location
if ($buildResult -ne 0) { 
    Write-Host "BUILD FAILED" -ForegroundColor Red
    exit 1 
}

Write-Host "`n=============================" -ForegroundColor Cyan
Write-Host "3. Running Playwright E2E Tests" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Push-Location services/web
npx playwright test --project=chromium
$e2eResult = $LASTEXITCODE
Pop-Location
if ($e2eResult -ne 0) { 
    Write-Host "E2E TESTS FAILED" -ForegroundColor Red
    exit 1 
}

Write-Host "`n=============================" -ForegroundColor Green
Write-Host "ALL TESTS PASSED" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
exit 0
