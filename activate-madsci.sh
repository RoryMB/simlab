#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate MADSci environment (Python 3.12)
source "$SCRIPT_DIR/.venv-madsci/bin/activate"

# Add robot directories to PYTHONPATH for interface imports
export PYTHONPATH="$SCRIPT_DIR/core/robots/ur5e:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/ot2:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/pf400:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/hidex:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/sealer:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/peeler:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/thermocycler:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/todo:$PYTHONPATH"
