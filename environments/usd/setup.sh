#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "USD Environment Setup"
echo "========================================="
echo "This will:"
echo "  1. Create a uv-managed virtual environment"
echo "  2. Install usd-core Python package and cmake"
echo "  3. Clone OpenUSD v24.11 from GitHub"
echo "  4. Build USD from source (~20-40 minutes)"
echo "========================================="
echo ""

# Step 1: Create virtual environment and install Python dependencies
echo "Step 1/4: Creating virtual environment and installing dependencies..."
uv venv
source .venv/bin/activate
./compile.sh
./sync.sh

# Step 2: Clone OpenUSD repository if not already present
if [ ! -d "usd-source" ]; then
    echo ""
    echo "Step 2/4: Cloning OpenUSD v24.11 repository..."
    git clone --depth 1 --branch v24.11 https://github.com/PixarAnimationStudios/OpenUSD.git usd-source
else
    echo ""
    echo "Step 2/4: OpenUSD repository already exists, skipping clone"
fi

# Step 3: Build USD from source if not already built
if [ ! -d "usd-install/bin" ]; then
    echo ""
    echo "Step 3/4: Building USD from source (this will take 20-40 minutes)..."
    echo "Build started at: $(date)"
    python3 usd-source/build_scripts/build_usd.py \
        --build-variant release \
        --no-imaging \
        --no-examples \
        --no-tutorials \
        --no-materialx \
        usd-install
    echo "Build completed at: $(date)"
else
    echo ""
    echo "Step 3/4: USD already built, skipping build"
fi

deactivate

# Step 4: Clean up build artifacts
echo ""
echo "Step 4/4: Cleaning up build artifacts..."
echo "Removing:"
echo "  - usd-source/ (source code - no longer needed)"
echo "  - usd-install/build/ (build artifacts)"
echo "  - usd-install/src/ (third-party sources)"
echo "  - usd-install/cmake/ (cmake config - only needed for building against USD)"
echo "  - usd-install/include/ (C++ headers - only needed for development)"
echo "  - usd-install/plugin/ (empty plugin directory)"
echo "  - usd-build.log (build log)"

rm -rf usd-source
rm -rf usd-install/build
rm -rf usd-install/src
rm -rf usd-install/cmake
rm -rf usd-install/include
rm -rf usd-install/plugin
rm -f usd-install/pxrConfig.cmake
rm -f usd-build.log

echo "Cleanup complete. Saved ~1.1GB of disk space."

echo ""
echo "========================================="
echo "USD Environment Setup Complete!"
echo "========================================="
echo "Tools installed to: $SCRIPT_DIR/usd-install/bin/"
echo "  - usdcat"
echo "  - usdtree"
echo "  - usddiff"
echo "  - usdchecker"
echo ""
echo "Activate with (from project root):"
echo "  source activate-usd.sh"
echo "========================================="
