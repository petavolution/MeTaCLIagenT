#!/bin/bash
# Run the EATS API server
# This is a convenience wrapper for: python run_core.py server

set -e
cd "$(dirname "$0")"

echo "==================================="
echo "EATS - Evolutionary Agent Tree System"
echo "==================================="
echo ""
echo "Starting server at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python run_core.py server
