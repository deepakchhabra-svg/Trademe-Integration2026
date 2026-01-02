#!/bin/bash
set -e

echo "============================"
echo "Running Contract Tests..."
echo "============================"
python -m pytest tests/test_contract_*.py

echo ""
echo "============================"
echo "Running Property Tests..."
echo "============================"
python -m pytest tests/test_property_*.py

echo ""
echo "============================"
echo "Running Integration Tests..."
echo "============================"
python -m pytest tests/test_integration_*.py

echo ""
echo "ALL TESTS PASSED"
