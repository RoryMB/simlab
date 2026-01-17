# Scaling MVP - Parallel Environment Testing

This project demonstrates parallel environment execution with 5 independent workcell simulations running simultaneously.

## Architecture

- **5 parallel Isaac Sim environments** with spatial offsets (5m apart)
- **Single ZMQ ROUTER** on port 5555 (multiplexed communication)
- **5 separate MongoDB instances** (ports 27017-27021)
- **5 workcell managers** (ports 8015, 8025, 8035, 8045, 8055)
- **Shared MADSci services** (Event, Resource, Location, etc.)

Each environment contains:
- PF400 robot arm
- Peeler device
- Thermocycler device

## Quick Start (Automated)

Use the orchestrate script to run everything automatically:

```bash
# Run environments 0 and 1 with workflow submission
python tools/orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/scaling-mvp && python run.py" \
    --madsci-cmd "cd projects/scaling-mvp/madsci && ./run_madsci.sh" \
    --node-cmd "cd projects/scaling-mvp && ./run_nodes.sh 0" \
    --node-cmd "cd projects/scaling-mvp && ./run_nodes.sh 1" \
    --workflow-cmd "source activate-madsci.sh && cd projects/scaling-mvp && python run_workflow.py --env-id 0 workflow.yaml && python run_workflow.py --env-id 1 workflow.yaml" \
    --timeout 240
```

Logs are written to `/tmp/simlab/<timestamp>/`.

## Running the System (Manual)

### Terminal 1: Start Isaac Sim

```bash
source activate-isaacsim.sh
cd projects/scaling-mvp
python run.py
```

### Terminal 2: Start MADSci Services

```bash
cd projects/scaling-mvp/madsci
./run_madsci.sh
```

### Terminals 3-7: Start Robot Nodes

Use the `run_nodes.sh` script to start all nodes for each environment:

```bash
cd projects/scaling-mvp
./run_nodes.sh 0   # Environment 0: REST ports 8100-8102
./run_nodes.sh 1   # Environment 1: REST ports 8110-8112
./run_nodes.sh 2   # Environment 2: REST ports 8120-8122
./run_nodes.sh 3   # Environment 3: REST ports 8130-8132
./run_nodes.sh 4   # Environment 4: REST ports 8140-8142
```

Each script instance runs PF400, Peeler, and Thermocycler nodes for that environment. Press Ctrl+C to stop all nodes for that environment.

### Terminal 8: Submit Workflow

```bash
source activate-madsci.sh
cd projects/scaling-mvp
python run_workflow.py --env-id 0 workflow.yaml
```

## Port Mapping

| Environment | Workcell Manager | PF400 | Peeler | Thermocycler | MongoDB |
|-------------|------------------|-------|--------|--------------|---------|
| 0           | 8015             | 8100  | 8101   | 8102         | 27017   |
| 1           | 8025             | 8110  | 8111   | 8112         | 27018   |
| 2           | 8035             | 8120  | 8121   | 8122         | 27019   |
| 3           | 8045             | 8130  | 8131   | 8132         | 27020   |
| 4           | 8055             | 8140  | 8141   | 8142         | 27021   |

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
- **workflow_transfer.yaml**: PF400 transfer demo (staging <-> thermocycler)

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
- REST node env vars require `NODE_` prefix: `NODE_ENV_ID`, `NODE_ZMQ_SERVER_URL`
- Location manager joint angles need calibration using command.py
