#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate Isaac Sim environment (Python 3.11, includes USD tools)
source "$SCRIPT_DIR/.venv-isaacsim/bin/activate"

# Add USD tools to PATH and PYTHONPATH
export PATH="$SCRIPT_DIR/tools/usd/usd-install/bin:$PATH"
export PYTHONPATH="$SCRIPT_DIR/tools/usd/usd-install/lib/python:$PYTHONPATH"

# Add core directories to PYTHONPATH for simple imports
export PYTHONPATH="$SCRIPT_DIR/core/common:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/ur5e:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/ot2:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/pf400:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/hidex:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/sealer:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/peeler:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/thermocycler:$PYTHONPATH"
export PYTHONPATH="$SCRIPT_DIR/core/robots/todo:$PYTHONPATH"
