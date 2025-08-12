#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating MADSci virtual environment..."
uv venv
source .venv/bin/activate
./compile.sh
./sync.sh
deactivate

echo "Environment setup complete"
echo "You can now activate environments using (from project root):"
echo "  ./activate-madsci.sh"
