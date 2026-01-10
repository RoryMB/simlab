# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

This project uses **multiple separate virtual environments** managed by [uv](https://github.com/astral-sh/uv) (Astral's fast Python package installer and resolver):

### Environment Activation
```bash
# For Isaac Sim work
source activate-isaacsim.sh

# For MADSci work
source activate-madsci.sh

# For USD command-line tools
source activate-usd.sh
```

### Managing Dependencies
To change dependencies, edit the appropriate `requirements.in` file, then:
```bash
source activate-{isaacsim,madsci,usd}.sh
cd environments/{isaacsim,madsci,usd}
./compile.sh    # Recompile lockfile
./sync.sh       # Update virtual environment
cd ../..
deactivate
```

### USD Environment
The USD environment provides command-line utilities for inspecting and manipulating USD files:
- `usdcat` - Print USD file contents (ASCII representation)
- `usdtree` - Display USD scene hierarchy as a tree
- `usddiff` - Compare two USD files and show differences
- `usdchecker` - Validate USD files for errors and compliance

These tools are useful for debugging robot asset files and understanding USD scene structure.

**CRITICAL: Never Read USD Files Directly**

USD files (.usd, .usda, .usdc) are often very large (1MB - 100MB+) and should NEVER be read using the Read tool.
Always use the USD command-line tools instead.
Attempting to read USD files directly will fail due to size limits and waste context.

**Usage Example:**
```bash
# Activate the USD environment
source activate-usd.sh

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
python scripts/orchestrate.py \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_ur5e.sh" \
    --node-cmd "source activate-madsci.sh && cd src/madsci/ && ./run_node_ot2.sh" \
    --isaac-cmd "source activate-isaacsim.sh && cd src/isaacsim/ && python run.py" \
    --madsci-cmd "cd src/madsci/ && ./run_madsci.sh" \
    --workflow-cmd "source activate-madsci.sh && cd projects/prototyping/ && python run_workflow.py workflow.yaml" \
```

**Important: Ready Keyword Behavior**

The orchestration script discards all output from each process until its ready keyword appears. This means:
- The ready keywords themselves will NEVER appear in the log output
- Only output AFTER the keywords will be visible in normal mode
- If a process never prints its keyword, its output will be completely hidden
- Use `--extremely-verbose` to see all output including pre-keyword startup messages

Adding the --extremely-verbose argument will help reveal startup errors by also printing everything before the ready keywords, but this causes incredibly large amounts of output to print. Use sparingly.

```bash
python scripts/orchestrate.py \
    --extremely-verbose \
    ...
```

### Terminal 1: Start Isaac Sim (Human or AI)

Humans should run Isaac Sim scripts like this:

```bash
. activate-isaacsim.sh
cd src/isaacsim/
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
# This terminal just handles docker containers, and thus does not need an environment.
cd src/madsci/
./run_madsci.sh
```

### Terminal 3: Start Robot Node (Human only)
```bash
. activate-madsci.sh
cd src/madsci/
./run_node_X.sh
```

### Terminal 4: Submit Workflow (Human or AI)
```bash
. activate-madsci.sh
cd src/
python run_workflow.py
```
