# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Environments

This project uses **two separate virtual environments** managed by uv:

- **Isaac Sim environment** (Python 3.11): Isaac Sim simulation + USD command-line tools
- **MADSci environment** (Python 3.12): Laboratory orchestration + robotics modules

### Environment Activation
```bash
# For Isaac Sim work
source activate-isaacsim.sh

# For MADSci work
source activate-madsci.sh
```

### USD Command-Line Tools

The Isaac Sim environment includes USD utilities for inspecting and manipulating USD files:
- `usdtree` - Display USD scene hierarchy as a tree
- `usddiff` - Compare two USD files and show differences
- `usdchecker` - Validate USD files for errors and compliance

These tools are useful for debugging robot asset files and understanding USD scene structure.

**CRITICAL: Never Read USD Files Directly**

USD files (.usd, .usda, .usdc) are often very large (1MB - 100MB+) and should NEVER be read using the Read tool or usdcat.
Always use the USD command-line tools instead, and avoid using usdcat.
Attempting to read USD files directly with Read or usdcat will fail due to size limits and/or waste context.

**Usage Example:**
```bash
# Activate the Isaac Sim environment
source activate-isaacsim.sh

# Display the hierarchy of a USD file
usdtree assets/robots/Brooks/PF400/PF400.usd
```

## Running the System

### Claude Code Run Instructions

Claude Code should use the orchestration script to run the full system:

```bash
python tools/orchestrate.py \
    --isaac-cmd "source activate-isaacsim.sh && cd projects/my-project && python run.py" \
    --gateway-cmd "source activate-madsci.sh && python -m slcore.gateway.rest_gateway --num-envs 1 --robot-types pf400,peeler,thermocycler" \
    --madsci-cmd "cd projects/my-project/madsci/ && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/my-project && python run_workflow.py workflow.yaml"
```

**Logging Behavior**

All process output is written to log files in `/tmp/simlab/<timestamp>/`:
- `isaac_startup.log`, `isaac_runtime.log` - Isaac Sim output before/after ready
- `gateway_startup.log`, `gateway_runtime.log` - REST Gateway output
- `madsci_startup.log`, `madsci_runtime.log` - MADSci output
- `workflow.log` - Workflow output

Console shows only:
- Process start/ready messages
- Error lines (detected via keywords: error, exception, traceback, failed)
- End summary with outcome, errors, workflow tail, and log file paths

### Independent Isaac Sim processes

Isaac Sim produces thousands of lines of startup logs. When running Isaac Sim outside of `tools/orchestrate.py`, filter out everything before "Simulation App Startup Complete":

```bash
source activate-isaacsim.sh && cd projects/prism && python run_phys.py 2>&1 | sed -n '/Simulation App Startup Complete/,$p'
```
