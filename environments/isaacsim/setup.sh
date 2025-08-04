#!/bin/bash
set -e

echo "Creating Isaac Sim virtual environment..."
echo "This could take a long time (under an hour)"
uv venv -p python@3.10
source .venv/bin/activate
./compile.sh
./sync.sh
deactivate

echo "Environment setup complete!"
echo "You can now activate environments using (from project root):"
echo "  ./activate-isaacsim.sh"
