$env:NEXT_PUBLIC_TEST_MODE = "1"
Write-Host "[SMOKE LOOP] Running smoke tests..." -ForegroundColor Cyan
npm run test:e2e:smoke
if ($LASTEXITCODE -ne 0) {
    Write-Host "[SMOKE LOOP] Smoke tests failed." -ForegroundColor Red
    Write-Host "To run last failed: npm run test:e2e:lf" -ForegroundColor Yellow
    exit $LASTEXITCODE
}
Write-Host "[SMOKE LOOP] Smoke tests passed." -ForegroundColor Green
