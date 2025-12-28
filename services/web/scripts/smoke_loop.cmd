@echo off
set NEXT_PUBLIC_TEST_MODE=1
echo [SMOKE LOOP] Running smoke tests...
npm run test:e2e:smoke
if %ERRORLEVEL% NEQ 0 (
    echo [SMOKE LOOP] Smoke tests failed.
    echo To run last failed: npm run test:e2e:lf
    exit /b %ERRORLEVEL%
)
echo [SMOKE LOOP] Smoke tests passed.
