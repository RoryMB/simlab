#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for CUDA 12.x (required for Isaac Lab and cuRobo)
if ! command -v nvcc &> /dev/null; then
    echo "Error: nvcc not found in PATH"
    echo "CUDA 12.x toolkit is required. Install it and add to PATH."
    exit 1
fi

CUDA_VERSION=$(nvcc --version | grep -oP 'release \K[0-9]+')
if [ "$CUDA_VERSION" -lt 12 ]; then
    echo "Error: CUDA 12.x required, but found CUDA ${CUDA_VERSION}.x"
    echo "Install CUDA 12.x toolkit and ensure it's first in PATH."
    exit 1
fi
echo "Found CUDA ${CUDA_VERSION}.x"

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

# Step 4: Install PyTorch with CUDA support
echo ""
echo "Installing PyTorch with CUDA support..."
uv pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128

# Step 5: Clone Isaac Lab at specific release tag
ISAACLAB_VERSION="v2.3.1"
if [ ! -d "IsaacLab" ]; then
    echo ""
    echo "Cloning Isaac Lab ${ISAACLAB_VERSION}..."
    git clone --branch ${ISAACLAB_VERSION} --depth 1 \
        https://github.com/isaac-sim/IsaacLab.git
else
    echo ""
    echo "Isaac Lab directory exists, ensuring correct version..."
    cd IsaacLab
    git fetch --tags
    git checkout ${ISAACLAB_VERSION}
    cd "$SCRIPT_DIR"
fi

# Step 6: Install Isaac Lab extensions
# Note: Isaac Lab v2.3.1's isaaclab.sh doesn't support uv environments natively,
# so we install pip first (uv venvs don't include pip by default)
echo ""
echo "Installing pip and build dependencies for Isaac Lab..."
uv pip install pip setuptools wheel

# Pre-install egl_probe with --no-build-isolation so it can find cmake from the venv
echo ""
echo "Pre-installing egl_probe..."
pip install --no-build-isolation egl_probe

echo ""
echo "Installing Isaac Lab extensions..."
cd IsaacLab
./isaaclab.sh --install
cd "$SCRIPT_DIR"

# Step 7: Clone and install cuRobo at specific release tag
CUROBO_VERSION="v0.7.7"
if [ ! -d "curobo" ]; then
    echo ""
    echo "Cloning cuRobo ${CUROBO_VERSION}..."
    git clone --branch ${CUROBO_VERSION} --depth 1 \
        https://github.com/NVlabs/curobo.git
else
    echo ""
    echo "cuRobo directory exists, ensuring correct version..."
    cd curobo
    git fetch --tags
    git checkout ${CUROBO_VERSION}
    cd "$SCRIPT_DIR"
fi

echo ""
echo "Installing cuRobo..."
# CUDA 12.x requires this environment variable for cuRobo compatibility
export CUROBO_TORCH_CUDA_GRAPH_RESET=1
uv pip install -e curobo --no-build-isolation

# Step 8: Build USD tools if not present
if [ ! -d "tools/usd/usd-install/bin" ]; then
    echo ""
    echo "Building USD tools from source..."

    # Clone USD source if needed
    if [ ! -d "tools/usd/usd-source" ]; then
        echo "Cloning OpenUSD..."
        git clone --depth 1 --branch v24.11 \
            https://github.com/PixarAnimationStudios/OpenUSD.git \
            tools/usd/usd-source
    fi

    # Build USD
    echo "Building USD..."
    python3 tools/usd/usd-source/build_scripts/build_usd.py \
        --build-variant release \
        --no-imaging \
        --no-examples \
        --no-tutorials \
        --no-materialx \
        tools/usd/usd-install

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
