#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv pip sync "$SCRIPT_DIR/requirements.txt"
