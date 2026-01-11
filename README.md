# Simlab

A simulation platform for autonomous laboratory environments that enables research into fully closed-loop scientific experimentation at massive scales.

This PhD research project integrates Isaac Sim (NVIDIA's 3D simulation software) with [MADSci](https://github.com/AD-SDL/MADSci) (Argonne National Labotory's experiment orchestration software) to investigate how autonomous agents can convert scientific protocols into executable robot commands and handle execution failures. By using MADSci, protocols run with the same execution and orchestration software that operates real laboratory robots, ensuring direct transferability between simulation and physical systems.

**Research Focus:**

- Protocol automation
- Failure handling
- Scalable laboratory simulation

## Key Capabilities

- **Isaac Sim Integration**: Full 3D simulation environment for laboratory robotics with physics-based interactions
- **MADSci Integration**: Laboratory experiment orchestration with standardized device interfaces
- **ZMQ Communication**: Real-time bidirectional communication between simulation and orchestration systems
- **Protocol Conversion**: Autonomous agent-based conversion of scientific protocols into executable robot workflows
- **Scalable Architecture**: Designed for warehouse-scale laboratory automation research

## Quick Start

### Environment Setup

This project uses two separate UV-managed virtual environments.

**Automated setup** (recommended for first-time setup):
```bash
./setup-isaacsim.sh  # Creates Isaac Sim environment + builds USD tools (30-50 min)
./setup-madsci.sh    # Creates MADSci environment
```

**Manual setup** (if you prefer step-by-step control):

Isaac Sim environment (Python 3.11):
```bash
uv venv .venv-isaacsim -p python@3.11
source .venv-isaacsim/bin/activate
uv pip compile requirements-isaacsim.in --extra-index-url https://pypi.nvidia.com -o requirements-isaacsim.txt
uv pip sync requirements-isaacsim.txt
deactivate
```

MADSci environment (Python 3.12):
```bash
uv venv .venv-madsci -p python@3.12
source .venv-madsci/bin/activate
uv pip compile requirements-madsci.in --override overrides-madsci.txt -o requirements-madsci.txt
uv pip sync requirements-madsci.txt
deactivate
```

**Activate environments:**
```bash
source activate-isaacsim.sh  # Isaac Sim + USD tools
source activate-madsci.sh    # MADSci + robotics modules
```

**Note:** USD command-line tools (usdtree, usddiff, usdchecker) are included in the Isaac Sim environment.

### Upgrading Dependencies

**To upgrade Isaac Sim version:**
1. Edit `requirements-isaacsim.in` and update `isaacsim[all,extscache]==X.X.X`
2. Run:
   ```bash
   source activate-isaacsim.sh
   uv pip compile requirements-isaacsim.in --extra-index-url https://pypi.nvidia.com -o requirements-isaacsim.txt --upgrade
   uv pip sync requirements-isaacsim.txt
   deactivate
   ```

**To upgrade MADSci version:**
1. Edit `requirements-madsci.in` and update `madsci-*==X.X.X` versions
2. Run:
   ```bash
   source activate-madsci.sh
   uv pip compile requirements-madsci.in --override overrides-madsci.txt -o requirements-madsci.txt --upgrade
   uv pip sync requirements-madsci.txt
   deactivate
   ```

**To upgrade individual packages:**
```bash
source activate-{isaacsim,madsci}.sh
uv pip compile requirements-{isaacsim,madsci}.in --upgrade-package PACKAGE_NAME -o requirements-{isaacsim,madsci}.txt
uv pip sync requirements-{isaacsim,madsci}.txt
deactivate
```

### Running the System

`python tools/orchestrate.py` – designed for agents like Claude Code.

See [CLAUDE.md](CLAUDE.md) for manual operation and technical details.

## Architecture Overview

### Core Components

- **Isaac Sim Integration** (`core/common/`): Shared utilities, simulation scripts, and ZMQ communication interface
- **MADSci Integration** (`projects/<project>/madsci/`): Per-project laboratory orchestration configuration and services
- **Robot Modules** (`core/robots/`): Per-robot directories containing both Isaac Sim ZMQ servers and MADSci node files

### Communication Pattern

The system uses ZMQ REQ-REP pattern for Isaac Sim ↔ MADSci communication:

- **Isaac Sim Server**: Handles robot movement commands and returns status
- **MADSci Client**: Sends movement commands and processes responses

### Workflow Pattern

1. Define laboratory layout in YAML (robots, locations, resources)
2. Define workflow steps in YAML (robot actions, parameters)
3. Submit workflow to MADSci workcell manager
4. MADSci coordinates robot nodes to execute workflow steps
5. Robot nodes communicate with Isaac Sim via ZMQ for physical simulation

For detailed technical specifications, see [CLAUDE.md](CLAUDE.md).

## Project Structure

```
simlab/
├── .venv-isaacsim/   # Isaac Sim environment (Python 3.11, includes USD tools)
├── .venv-madsci/     # MADSci environment (Python 3.12, robotics modules)
├── forks/            # Third-party library forks with custom modifications
│   └── opentrons/        # Opentrons library fork (patched for numpy 2.0 compatibility)
├── core/             # Core implementation
│   ├── common/           # Shared utilities (run.py, utils.py, primary_functions.py)
│   └── robots/           # Per-robot directories
│       ├── ur5e/             # UR5e arm (zmq_ur5e_server.py, sim_ur5e_*.py, run_node_ur5e.sh)
│       ├── ot2/              # Opentrons OT-2 liquid handler
│       ├── pf400/            # Brooks PF400 plate handler
│       ├── hidex/            # Hidex plate reader
│       ├── sealer/           # Plate sealer
│       ├── peeler/           # Plate peeler
│       └── thermocycler/     # Thermocycler
├── assets/           # 3D simulation assets
│   ├── scenes/           # Laboratory layouts
│   ├── architecture/     # Structural elements (walls, floors, ceilings)
│   ├── robots/           # Robot models
│   ├── labware/          # Experimental apparatus (tips, plates, reagents)
│   ├── props/            # Environmental objects
│   └── tools/            # Asset processing tools (.blend to .usd conversion)
├── tools/            # User tools and utilities for the command line
│   └── usd/              # USD command-line tools built from source
├── projects/         # Self-contained experimental projects
│   ├── template/         # Template for new projects (includes madsci/ setup)
│   ├── prototyping/      # Development and testing workflows
│   └── [custom]/         # Custom projects, each with optional madsci/ subdirectory
├── requirements-isaacsim.in  # Isaac Sim dependencies
├── requirements-madsci.in    # MADSci dependencies
└── activate-{isaacsim,madsci}.sh  # Environment activation scripts
```

## Contributing & Collaboration

### Research Collaboration

This project supports research into:

- Autonomous agent-based protocol conversion, generation, and execution
- Failure handling and recovery in automated experimentation
- Scalable simulation for laboratory automation

Researchers interested in collaboration on laboratory automation, autonomous agent-driven experimentation, or related areas are welcome to reach out.

### Technical Contributions

- **Issue Reports**: Bug reports, feature requests, and documentation improvements
- **Protocol Examples**: Additional scientific protocol implementations
- **Device Integration**: New robot or laboratory device integrations
- **Simulation Assets**: Laboratory environments, robot models, or consumables
