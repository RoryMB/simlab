#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate MADSci environment (Python 3.12)
source "$SCRIPT_DIR/.venv-madsci/bin/activate"

# Add project root to PYTHONPATH for package imports (e.g., from slcore.robots.common import ...)
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
