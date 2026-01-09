#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv pip compile "$@" "$SCRIPT_DIR/requirements.in" --extra-index-url https://pypi.nvidia.com -o "$SCRIPT_DIR/requirements.txt"
