#!/usr/bin/env bash
# run.sh - Local testing script for Whisp

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Pass all arguments (like --dev) to the main script
PYTHONPATH=src python3 src/whisp/main.py "$@"
