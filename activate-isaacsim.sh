#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate Isaac Sim environment (Python 3.11, includes USD tools)
source "$SCRIPT_DIR/.venv-isaacsim/bin/activate"

# Add USD tools to PATH and PYTHONPATH
export PATH="$SCRIPT_DIR/tools/usd/usd-install/bin:$PATH"
export PYTHONPATH="$SCRIPT_DIR/tools/usd/usd-install/lib/python:$PYTHONPATH"

# Add project root to PYTHONPATH for package imports (e.g., from slcore.robots.common import ...)
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
