#!/bin/bash
# Start robot nodes for a specific parallel environment
#
# Usage: ./run_nodes.sh <env_id>
# Example: ./run_nodes.sh 0

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <env_id>"
    echo "  env_id: Environment ID (0-4)"
    exit 1
fi

ENV_ID=$1

if [ "$ENV_ID" -lt 0 ] || [ "$ENV_ID" -gt 4 ]; then
    echo "Error: env_id must be between 0 and 4"
    exit 1
fi

# Calculate REST ports: env 0 = 8100-8102, env 1 = 8110-8112, etc.
BASE_PORT=$((8100 + ENV_ID * 10))
PF400_PORT=$BASE_PORT
PEELER_PORT=$((BASE_PORT + 1))
THERMOCYCLER_PORT=$((BASE_PORT + 2))

echo "Starting nodes for environment $ENV_ID"
echo "  PF400:        REST port $PF400_PORT"
echo "  Peeler:       REST port $PEELER_PORT"
echo "  Thermocycler: REST port $THERMOCYCLER_PORT"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source MADSci environment variables
set -a
source "$SCRIPT_DIR/madsci/config/.env"
set +a

# Activate MADSci venv
source "$PROJECT_ROOT/activate-madsci.sh"

# Common environment for all nodes (NODE_ prefix required by pydantic-settings)
export NODE_ZMQ_SERVER_URL="tcp://localhost:5555"
export NODE_ENV_ID="$ENV_ID"

# Trap to kill all background processes on exit
cleanup() {
    echo ""
    echo "Shutting down nodes for environment $ENV_ID..."
    jobs -p | xargs -r kill 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start PF400 node
echo "Starting pf400_$ENV_ID on port $PF400_PORT..."
(
    cd "$PROJECT_ROOT/slcore/robots/pf400"
    NODE_URL="http://127.0.0.1:$PF400_PORT/" \
    python sim_pf400_rest_node.py 2>&1 | sed "s/^/[pf400_$ENV_ID] /"
) &

# Start Peeler node
echo "Starting peeler_$ENV_ID on port $PEELER_PORT..."
(
    cd "$PROJECT_ROOT/slcore/robots/peeler"
    NODE_URL="http://127.0.0.1:$PEELER_PORT/" \
    python sim_peeler_rest_node.py 2>&1 | sed "s/^/[peeler_$ENV_ID] /"
) &

# Start Thermocycler node
echo "Starting thermocycler_$ENV_ID on port $THERMOCYCLER_PORT..."
(
    cd "$PROJECT_ROOT/slcore/robots/thermocycler"
    NODE_URL="http://127.0.0.1:$THERMOCYCLER_PORT/" \
    python sim_thermocycler_rest_node.py 2>&1 | sed "s/^/[thermocycler_$ENV_ID] /"
) &

echo ""
echo "All nodes started. Press Ctrl+C to stop."
echo ""

# Wait for all background processes
wait
