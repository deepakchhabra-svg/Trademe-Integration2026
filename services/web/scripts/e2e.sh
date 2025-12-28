#!/bin/bash
# E2E Execution Script
cd services/web
export NEXT_PUBLIC_TEST_MODE=1
npm run test:e2e -- --headed
