#!/bin/bash
set -e

echo "============================="
echo "1. Running ALL pytest Tests"
echo "============================="
python -m pytest tests/ -v --tb=short

echo ""
echo "============================="
echo "2. Building Next.js Frontend"
echo "============================="
cd services/web
npm run build
cd ../..

echo ""
echo "============================="
echo "3. Running Playwright E2E Tests"
echo "============================="
cd services/web
npx playwright test --project=chromium
cd ../..

echo ""
echo "============================="
echo "ALL TESTS PASSED"
echo "============================="
