#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "MADSci Environment Setup"
echo "========================================="
echo "This will create and configure the MADSci environment"
echo "========================================="
echo ""

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
echo "Step 1/3: Creating virtual environment (Python 3.12)..."
uv venv .venv-madsci -p python@3.12

# Step 2: Compile requirements
echo ""
echo "Step 2/3: Compiling dependencies..."
source .venv-madsci/bin/activate
uv pip compile requirements-madsci.in \
    --override overrides.txt \
    -o requirements-madsci.txt

# Step 3: Install dependencies
echo ""
echo "Step 3/3: Installing dependencies..."
uv pip sync requirements-madsci.txt

# Step 4: Patch opentrons_shared_data for numpy 2.0 compatibility
echo ""
echo "Patching opentrons_shared_data for NumPy 2.0 compatibility..."
LABWARE_DEF=".venv-madsci/lib/python3.12/site-packages/opentrons_shared_data/labware/labware_definition.py"
if [ -f "$LABWARE_DEF" ]; then
    # Check if already patched
    if grep -q "trapezoid as trapz" "$LABWARE_DEF"; then
        echo "Already patched"
    else
        # Apply patch
        sed -i 's/from numpy import pi, trapz/from numpy import pi\ntry:\n    from numpy import trapz\nexcept ImportError:\n    # numpy 2.0+ renamed trapz to trapezoid\n    from numpy import trapezoid as trapz/' "$LABWARE_DEF"
        echo "Patch applied successfully"
    fi
else
    echo "WARNING: Could not find opentrons_shared_data labware_definition.py"
    echo "NumPy 2.0 compatibility patch not applied"
fi

deactivate

echo ""
echo "========================================="
echo "MADSci Environment Setup Complete!"
echo "========================================="
echo "Activate with: source activate-madsci.sh"
echo "========================================="
