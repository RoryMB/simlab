# Scaling MVP - Parallel Environment Testing

This project demonstrates parallel environment execution with 5 independent workcell simulations running simultaneously.

## Architecture

- **5 parallel Isaac Sim environments** with spatial offsets (5m apart)
- **Single ZMQ ROUTER** on port 5555 (multiplexed communication)
- **Single REST Gateway** on port 8000 (path-based routing for all robots)
- **5 separate MongoDB instances** (ports 27017-27021)
- **5 workcell managers** (ports 8015, 8025, 8035, 8045, 8055)
- **Shared MADSci services** (Event, Resource, Location, etc.)

Each environment contains:
- PF400 robot arm
- Peeler device
- Thermocycler device

## Quick Start

Use the orchestrate script to run everything automatically:

```bash
python tools/orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/scaling-mvp && python run.py" \
    --gateway-cmd "source activate-madsci.sh && python -m slcore.gateway.rest_gateway --num-envs 5" \
    --madsci-cmd "cd projects/scaling-mvp/madsci && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/scaling-mvp && python run_parallel_workflows.py workflow_transfer.yaml" \
    --timeout 240
```

Logs are written to `/tmp/simlab/<timestamp>/`.

## Running Manually

### Terminal 1: Start Isaac Sim

```bash
source activate-isaacsim.sh
cd projects/scaling-mvp
python run.py
```

### Terminal 2: Start REST Gateway

```bash
source activate-madsci.sh
python -m slcore.gateway.rest_gateway --num-envs 5 --robot-types pf400,peeler,thermocycler
```

### Terminal 3: Start MADSci Services

```bash
cd projects/scaling-mvp/madsci
./run_madsci.sh
```

### Terminal 4: Submit Workflow

```bash
source activate-madsci.sh
cd projects/scaling-mvp
python run_workflow.py workflow_transfer.yaml
```

## Verification

1. **Visual**: Check Isaac Sim - should see 5 workcells at 5m intervals along X axis
2. **ZMQ routing**: Send command to one environment, verify only that robot responds
3. **Workflow**: Submit workflows to different environments simultaneously
4. **Isolation**: Trigger error in one environment, others continue normally

## Workflow Node Naming

Workflows use **logical node names** (`pf400`, `peeler`, `thermocycler`) that are consistent across all workcells:

```yaml
steps:
  - name: Open Thermocycler
    node: thermocycler  # NOT thermocycler_0
    action: open
```

This allows the same workflow to run on any environment - just specify `--env-id N` when submitting.

## Available Workflows

- **workflow.yaml**: Simple thermocycler open/close test
- **workflow_transfer.yaml**: PF400 transfer demo (peeler <-> thermocycler)

## Parallel Workflow Testing

The `run_parallel_workflows.py` script submits the same workflow to all 5 environments and tracks results:

```bash
source activate-madsci.sh
cd projects/scaling-mvp
python run_parallel_workflows.py workflow_transfer.yaml
```

This script:
- Automatically prefixes location names with `env_{id}.` for each environment
- Creates test microplates at each environment's starting location
- Reports success/failure for each environment

## PF400 Calibration

The `command.py` script allows direct ZMQ communication with Isaac Sim for calibrating robot positions:

```bash
# Start Isaac Sim first
source activate-isaacsim.sh && cd projects/scaling-mvp && python run.py

# In another terminal, run calibration commands
source activate-madsci.sh && cd projects/scaling-mvp
python command.py
```

The script moves PF400 to named xform locations and captures joint angles. Edit `command.py` to customize:
- `ENV_ID`: Which environment to control (0-4)
- `COMMANDS`: List of actions to execute

Available PF400 commands:
- `goto_prim`: Move to a scene xform (e.g., `/World/env_0/locations/staging`)
- `get_joints`: Print current joint angles
- `move_joints`: Move to specific joint angles
- `gripper_open`/`gripper_close`: Control gripper

Location xforms in run.py:
- `home`, `home_hover`
- `staging`, `staging_hover`
- `thermocycler_nest`, `thermocycler_nest_hover`
- `peeler_nest`, `peeler_nest_hover`

## Notes

- Each MongoDB is non-persistent (data lost on container restart)
- All environments share Redis, PostgreSQL, and shared managers (Event, Resource, Location, Data, Lab, Experiment)
- ZMQ identities use format `env_{id}.{robot_type}` (e.g., `env_0.pf400`, `env_3.thermocycler`)
- Gateway routes requests via URL path (e.g., `/env_0/pf400/action/transfer`)
- Location manager uses env-prefixed names (e.g., `env_0.peeler_nest`) with unique resource_ids per location
