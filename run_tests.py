#!/usr/bin/env python3
"""
EATS Core - Test Runner

Simple CLI test runner for the EATS core functionality.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose mode
    python run_tests.py TestDNA      # Run specific test class
    python run_tests.py --quick      # Skip slow tests
"""

import sys
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

if __name__ == "__main__":
    # Import and run the test suite
    from tests.test_core import main
    main()
