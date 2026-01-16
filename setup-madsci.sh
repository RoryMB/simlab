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

# Step 4: Apply opentrons patches
echo ""
echo "Applying opentrons patches..."

# Get site-packages path for patches
SITE_PACKAGES=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")

# Apply opentrons_shared_data numpy 2 compatibility patch
if [ -f "forks/opentrons_shared_data.patch" ]; then
    if patch -d "${SITE_PACKAGES}" -p0 < forks/opentrons_shared_data.patch; then
        echo "opentrons_shared_data patch applied successfully"
    else
        echo "WARNING: Failed to apply opentrons_shared_data patch"
    fi
fi

# Apply opentrons simulation patch
if [ -f "forks/opentrons.patch" ]; then
    # Create simulation directory for new files
    mkdir -p "${SITE_PACKAGES}/opentrons/hardware_control/simulation"

    # Apply patch (-p0 keeps paths as-is)
    if patch -d "${SITE_PACKAGES}" -p0 < forks/opentrons.patch; then
        echo "opentrons patch applied successfully"
    else
        echo "WARNING: Failed to apply opentrons patch - simulation features may not work"
    fi
else
    echo "WARNING: forks/opentrons.patch not found - simulation features will not work"
fi

deactivate

echo ""
echo "MADSci Environment Setup Complete!"
echo "Activate with: source activate-madsci.sh"
