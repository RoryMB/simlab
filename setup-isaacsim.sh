#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if venv already exists
if [ -d ".venv-isaacsim" ]; then
    echo "WARNING: .venv-isaacsim already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv-isaacsim
        echo "Deleted existing environment"
    else
        echo "Aborting setup"
        exit 1
    fi
fi

# Step 1: Create virtual environment
echo "Creating virtual environment (Python 3.11)..."
uv venv .venv-isaacsim -p python@3.11

# Step 2: Compile requirements
echo ""
echo "Compiling dependencies..."
source .venv-isaacsim/bin/activate
uv pip compile requirements-isaacsim.in \
    --extra-index-url https://pypi.nvidia.com \
    -o requirements-isaacsim.txt

# Step 3: Install dependencies
echo ""
echo "Installing dependencies..."
uv pip sync requirements-isaacsim.txt

# Step 4: Build USD tools if not present
if [ ! -d "tools/usd/usd-install/bin" ]; then
    echo ""
    echo "Building USD tools from source..."

    # Clone USD source if needed
    if [ ! -d "tools/usd/usd-source" ]; then
        echo "Cloning OpenUSD v24.11..."
        git clone --depth 1 --branch v24.11 \
            https://github.com/PixarAnimationStudios/OpenUSD.git \
            tools/usd/usd-source
    fi

    # Build USD
    echo "Building USD..."
    echo "Build started at: $(date)"
    python3 tools/usd/usd-source/build_scripts/build_usd.py \
        --build-variant release \
        --no-imaging \
        --no-examples \
        --no-tutorials \
        --no-materialx \
        tools/usd/usd-install
    echo "Build completed at: $(date)"

    # Cleanup
    echo "Cleaning up build artifacts..."
    rm -rf tools/usd/usd-source
    rm -rf tools/usd/usd-install/build
    rm -rf tools/usd/usd-install/src
    rm -rf tools/usd/usd-install/cmake
    rm -rf tools/usd/usd-install/include
    rm -rf tools/usd/usd-install/plugin
    rm -f tools/usd/usd-install/pxrConfig.cmake
    echo "Cleanup complete"
else
    echo ""
    echo "USD tools already built, skipping..."
fi

deactivate

echo "========================================="
echo "Isaac Sim Environment Setup Complete!"
echo "Activate with: source activate-isaacsim.sh"
echo ""
echo "IMPORTANT: Accept Isaac Sim EULA on first run:"
echo "  source activate-isaacsim.sh"
echo "  isaacsim"
