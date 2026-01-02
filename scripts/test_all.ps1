$ErrorActionPreference = "Stop"

Write-Host "============================" -ForegroundColor Cyan
Write-Host "Running Contract Tests..." -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
python -m pytest tests/ -k "contract"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`n============================" -ForegroundColor Cyan
Write-Host "Running Property Tests..." -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
python -m pytest tests/ -k "property"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`n============================" -ForegroundColor Cyan
Write-Host "Running Integration Tests..." -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
python -m pytest tests/ -k "integration"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`nALL TESTS PASSED" -ForegroundColor Green
exit 0
