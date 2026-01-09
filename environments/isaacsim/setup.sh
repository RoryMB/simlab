#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating Isaac Sim virtual environment..."
echo "This could take a long time to download"
uv venv -p python@3.11
source .venv/bin/activate
./compile.sh
./sync.sh
deactivate

echo "Environment setup complete"
echo "You can now activate environments using (from project root):"
echo "  ./activate-isaacsim.sh"
echo "Make sure to run Isaac Sim at least once manually to accept the EULA:"
echo "  isaacsim"
echo "Wait for 'Simulation App Startup Complete' to appear, which may take 2-5 minutes"
