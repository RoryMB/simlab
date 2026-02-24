# Simple - Single Environment Introduction

A minimal single-environment project to introduce the Simlab architecture. Runs one workcell with a PF400 robot arm, peeler, and thermocycler.

## What's in This Project

- **run_sim.py** - Starts Isaac Sim with the 3D robot environment
- **run_workflow.py** - Submits a workflow to MADSci for orchestrated execution
- **command.py** - Sends commands directly to Isaac Sim via ZMQ (no MADSci needed)
- **workflow.yaml** - PF400 picks up a plate from the peeler, places it in the thermocycler, and returns it

## Quick Start

Run the full system with the orchestrator:

```bash
python tools/orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/simple && python run_sim.py" \
    --gateway-cmd "source activate-madsci.sh && python -m slcore.gateway.rest_gateway --num-envs 1 --robot-types pf400,peeler,thermocycler" \
    --madsci-cmd "./tools/run_madsci.sh projects/simple" \
    --workflow-cmd "source activate-madsci.sh && cd projects/simple && python run_workflow.py workflow.yaml"
```

Logs are written to `/tmp/simlab/<timestamp>/`.

## Running Manually

Running each component in a separate terminal is useful for understanding how the pieces connect.

### Terminal 1: Start Isaac Sim

```bash
source activate-isaacsim.sh
cd projects/simple
python run_sim.py
```

Wait for "Simulation App Startup Complete" before continuing.

### Terminal 2: Start REST Gateway

```bash
source activate-madsci.sh
python -m slcore.gateway.rest_gateway --num-envs 1 --robot-types pf400,peeler,thermocycler
```

The gateway translates HTTP requests from MADSci into ZMQ messages for Isaac Sim.

### Terminal 3: Start MADSci Services

```bash
./tools/run_madsci.sh projects/simple
```

This starts Docker containers for the MADSci managers (workcell, location, resource, etc.).

### Terminal 4: Submit a Workflow

```bash
source activate-madsci.sh
cd projects/simple
python run_workflow.py workflow.yaml
```

For the plate transfer demo:

```bash
python run_workflow.py workflow_transfer.yaml
```

## Trying Direct Commands (No MADSci)

You can talk to Isaac Sim directly without MADSci, which is useful for testing and calibration:

1. Start Isaac Sim (Terminal 1 above)
2. In another terminal:

```bash
source activate-madsci.sh
cd projects/simple
python command.py
```

Edit the `COMMANDS` list in `command.py` to try different actions. Available commands:

| Robot | Action | Description |
|-------|--------|-------------|
| pf400 | goto_prim | Move to a named location in the scene |
| pf400 | get_joints | Print current joint angles |
| pf400 | move_joints | Move to specific joint angles |
| pf400 | gripper_open | Open the gripper |
| pf400 | gripper_close | Close the gripper |
| pf400 | get_status | Get robot status (moving, collision, etc.) |
| thermocycler | open | Open the lid |
| thermocycler | close | Close the lid |
| peeler | peel | Run the peeling action |

## Architecture

```
                         Workflow YAML
                              |
                              v
MADSci Workcell Manager (port 8015)
         |
         | HTTP POST /env_0/pf400/action/transfer
         v
REST Gateway (port 8000) --> ZMQ DEALER --> Isaac Sim ZMQ ROUTER (port 5555)
```

- Isaac Sim runs a ZMQ ROUTER server on port 5555
- The REST Gateway connects as ZMQ DEALER clients (one per robot)
- MADSci sends HTTP requests to the gateway, which forwards them to Isaac Sim
- `command.py` connects directly as a DEALER client, bypassing the gateway and MADSci
