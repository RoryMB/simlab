#!/bin/bash
set -e

echo "Creating MADSci virtual environment..."
uv venv
source .venv/bin/activate
./compile.sh
./sync.sh
deactivate

echo "Environment setup complete!"
echo "You can now activate environments using (from project root):"
echo "  ./activate-madsci.sh"
