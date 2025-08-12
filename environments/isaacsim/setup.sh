#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating Isaac Sim virtual environment..."
echo "This could take a long time to download"
uv venv -p python@3.10
source .venv/bin/activate
./compile.sh
./sync.sh
deactivate

echo "Environment setup complete"
echo "You can now activate environments using (from project root):"
echo "  ./activate-isaacsim.sh"
