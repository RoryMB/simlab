#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv-madsci" ]; then
    echo "Error: Virtual environment not found at $SCRIPT_DIR/.venv-madsci"
    echo "Run ./setup-madsci.sh first."
    return 1
fi

# Activate MADSci environment (Python 3.12)
source "$SCRIPT_DIR/.venv-madsci/bin/activate"

# Add project root to PYTHONPATH for package imports (e.g., from slcore.robots.common import ...)
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
