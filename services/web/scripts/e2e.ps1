# E2E Execution Script (PowerShell)
Set-Location "services/web"
$env:NEXT_PUBLIC_TEST_MODE = "1"
npm run test:e2e -- --headed
