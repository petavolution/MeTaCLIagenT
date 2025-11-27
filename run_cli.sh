#!/bin/bash
# Run the EATS CLI interface
# This is a convenience wrapper for: python run_core.py cli

set -e
cd "$(dirname "$0")"

echo "==================================="
echo "EATS - CLI Interface"
echo "==================================="
echo ""

python run_core.py cli "$@"
