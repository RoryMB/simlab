#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv pip compile "$@" "$SCRIPT_DIR/requirements.in" --override "$SCRIPT_DIR/overrides.txt" -o "$SCRIPT_DIR/requirements.txt"
