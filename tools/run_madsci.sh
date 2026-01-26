#!/bin/bash
# Consolidated MADSci startup script
# Usage: ./tools/run_madsci.sh <project-path>
# Example: ./tools/run_madsci.sh projects/prism

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <project-path>"
    echo "Example: $0 projects/prism"
    exit 1
fi

PROJECT_PATH="$1"
MADSCI_DIR="$PROJECT_PATH/madsci"

if [ ! -d "$MADSCI_DIR" ]; then
    echo "Error: MADSci directory not found: $MADSCI_DIR"
    exit 1
fi

if [ ! -f "$MADSCI_DIR/compose.yaml" ]; then
    echo "Error: compose.yaml not found in $MADSCI_DIR"
    exit 1
fi

cd "$MADSCI_DIR"

docker rm -f workcell_manager experiment_manager data_manager lab_manager resource_manager event_manager redis mongodb postgres
docker compose down --remove-orphans
docker compose up
docker compose down --remove-orphans
