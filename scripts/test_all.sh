#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PYTHONPATH="${ROOT_DIR}"

# Deterministic E2E auth boundary for local runs (override if you want).
export RETAIL_OS_POWER_TOKEN="${RETAIL_OS_POWER_TOKEN:-local-e2e-power}"
# Never allow header role escalation during tests.
export RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES="${RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES:-false}"

echo "==> Python unit tests"
python3 -m pytest "${ROOT_DIR}/tests" -q

echo "==> Web build"
npm --prefix "${ROOT_DIR}/services/web" run build

echo "==> Seed E2E DB (offline)"
export RETAILOS_E2E_DATABASE_URL="${RETAILOS_E2E_DATABASE_URL:-sqlite:////tmp/retailos_e2e.sqlite}"
python3 "${ROOT_DIR}/tests/seed_e2e.py"

echo "==> Playwright smoke"
pushd "${ROOT_DIR}/services/web" >/dev/null
npx playwright test --project=chromium --grep @smoke --workers=1 --max-failures=1
popd >/dev/null

echo "All checks passed."

