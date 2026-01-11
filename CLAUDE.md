# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

This project uses **two separate virtual environments** managed by [uv](https://github.com/astral-sh/uv) (Astral's fast Python package installer and resolver):

- **Isaac Sim environment** (Python 3.11): Isaac Sim simulation + USD command-line tools
- **MADSci environment** (Python 3.12): Laboratory orchestration + robotics modules

### Environment Activation
```bash
# For Isaac Sim work (includes USD tools)
source activate-isaacsim.sh

# For MADSci work
source activate-madsci.sh
```

### Initial Setup

**Automated setup scripts** (recommended):
```bash
./setup-isaacsim.sh  # Creates Isaac Sim environment + builds USD tools
./setup-madsci.sh    # Creates MADSci environment
```

### Managing Dependencies

**Isaac Sim environment:**
```bash
# Edit requirements-isaacsim.in at project root
source activate-isaacsim.sh
uv pip compile requirements-isaacsim.in --extra-index-url https://pypi.nvidia.com -o requirements-isaacsim.txt
uv pip sync requirements-isaacsim.txt
deactivate
```

**MADSci environment:**
```bash
# Edit requirements-madsci.in at project root
source activate-madsci.sh
uv pip compile requirements-madsci.in --override overrides-madsci.txt -o requirements-madsci.txt
uv pip sync requirements-madsci.txt
deactivate
```

**Upgrading versions:**
Add `--upgrade` flag to recompile with latest compatible versions, or `--upgrade-package PACKAGE_NAME` to upgrade specific packages.

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
# Activate the Isaac Sim environment (includes USD tools)
source activate-isaacsim.sh

# Display the hierarchy of a USD file
usdtree assets/robots/Brooks/PF400/PF400.usd
```

## Running the System

A traditional run requires 4 terminals running simultaneously.

**Important:** `export DISPLAY=:0` is required before any command that uses Isaac Sim to enable Isaac Sim's graphical interface.

### Claude Code Run Instructions

When running individual Isaac Sim / MADSci scripts:
- Claude Code should ONLY run Isaac Sim scripts (Terminal 1 below) and workflow submission scripts (Terminal 4 below)
- Claude Code should NEVER start MADSci services (Terminal 2 below) or robot nodes (Terminal 3 below), as these require special shutdown mechanics that Claude Code is not equipped to handle.

Claude Code can use the following orchestration script to run all terminals commands simultaneously, wich organizes startup and shutdown mechanics automatically:

```bash
# An example of running 2 nodes, the run.py Isaac Sim script, and the run_madsci.sh MADSci script.
# Any number of node commands can be given.
# Only one Isaac Sim command, one MADSci command, and one workflow command can be given.
# Note: Node commands must source the project's .env first (provides MADSci server URLs).
python tools/orchestrate.py \
    --node-cmd "set -a; source projects/my-project/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/ur5e/ && ./run_node_ur5e.sh" \
    --node-cmd "set -a; source projects/my-project/madsci/config/.env; set +a && source activate-madsci.sh && cd core/robots/ot2/ && ./run_node_ot2.sh" \
    --isaac-cmd "source activate-isaacsim.sh && cd core/common/ && python run.py" \
    --madsci-cmd "cd projects/my-project/madsci/ && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/my-project/ && python run_workflow.py workflow.yaml" \
```

**Important: Ready Keyword Behavior**

The orchestration script discards all output from each process until its ready keyword appears. This means:
- The ready keywords themselves will NEVER appear in the log output
- Only output AFTER the keywords will be visible in normal mode
- If a process never prints its keyword, its output will be completely hidden
- Use `--extremely-verbose` to see all output including pre-keyword startup messages

Adding the --extremely-verbose argument will help reveal startup errors by also printing everything before the ready keywords, but this causes incredibly large amounts of output to print. Use sparingly.

```bash
python tools/orchestrate.py \
    --extremely-verbose \
    ...
```

### Terminal 1: Start Isaac Sim (Human or AI)

Humans should run Isaac Sim scripts like this:

```bash
. activate-isaacsim.sh
cd core/common/
python run.py
```

Claude Code should run Isaac Sim scripts like this:

```bash
cd /home/rmbutler/simlab && ./.ai_run_isaac_sim.sh path/to/script.py
```

**Filtering Isaac Sim Startup Logs:**

Isaac Sim produces thousands of lines of startup logs that can fill up context windows. To filter out everything before "Simulation App Startup Complete", use:

```bash
source activate-isaacsim.sh && cd projects/prism && python run_phys.py 2>&1 | sed -n '/Simulation App Startup Complete/,$p'
```

This pattern works for any Isaac Sim script - just replace the script path.

### Terminal 2: Start MADSci Services (Human only)
```bash
# MADSci config is per-project. No virtual environment needed (docker handles it).
cd projects/my-project/madsci/
./run_madsci.sh
```

### Terminal 3: Start Robot Node (Human only)
```bash
# Source the project's MADSci .env first (provides server URLs), then activate venv and run node
set -a; source projects/my-project/madsci/config/.env; set +a
. activate-madsci.sh
cd core/robots/ur5e/  # or ot2/, pf400/, etc.
./run_node_ur5e.sh    # or run_node_ot2.sh, run_node_pf400.sh, etc.
```

### Terminal 4: Submit Workflow (Human or AI)
```bash
. activate-madsci.sh
cd projects/prototyping/
python run_workflow.py workflow.yaml
```
