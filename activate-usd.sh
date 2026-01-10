#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/environments/usd/.venv/bin/activate"

# Add USD built-from-source binaries and Python modules to PATH and PYTHONPATH
export PATH="$SCRIPT_DIR/environments/usd/usd-install/bin:$PATH"
export PYTHONPATH="$SCRIPT_DIR/environments/usd/usd-install/lib/python:$PYTHONPATH"
