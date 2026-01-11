#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if venv already exists
if [ -d ".venv-madsci" ]; then
    echo "WARNING: .venv-madsci already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv-madsci
        echo "Deleted existing environment"
    else
        echo "Aborting setup"
        exit 1
    fi
fi

# Check if opentrons fork exists
if [ ! -d "forks/opentrons" ]; then
    echo "ERROR: forks/opentrons/ not found"
    echo "The opentrons fork is required for the MADSci environment"
    exit 1
fi

# Step 1: Create virtual environment
echo "Creating virtual environment..."
uv venv .venv-madsci -p python@3.12

# Step 2: Compile requirements
echo ""
echo "Compiling dependencies..."
source .venv-madsci/bin/activate
uv pip compile requirements-madsci.in \
    --override overrides-madsci.txt \
    -o requirements-madsci.txt

# Step 3: Install dependencies
echo ""
echo "Installing dependencies..."
uv pip sync requirements-madsci.txt

deactivate

echo ""
echo "MADSci Environment Setup Complete!"
echo "Activate with: source activate-madsci.sh"
