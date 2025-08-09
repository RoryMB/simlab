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

This project uses two separate UV-managed virtual environments. Initial setup:

```bash
cd environments/isaacsim && ./setup.sh && cd ../..
cd environments/madsci && ./setup.sh && cd ../..
```

For detailed environment management, see [environments/README.md](environments/README.md).

### Running the System

`python orchestrate.py` – designed for agents like Claude Code.

See [src/README.md](src/README.md) for manual operation and technical details.

## Architecture Overview

### Core Components

- **Isaac Sim Integration** (`src/isaacsim/`): 3D simulation environment with ZMQ communication interface to MADSci
- **MADSci Integration** (`src/madsci/`): Laboratory orchestration with custom robot nodes and ZMQ communication to Isaac Sim
- **Reference Material** (`reference/`): MADSci core framework and 20+ device integration modules for reference during development

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

For detailed technical specifications, see [src/README.md](src/README.md).

## Project Structure

```
simlab/
├── environments/     # UV-managed virtual environments
│   ├── isaacsim/         # Isaac Sim environment setup scripts
│   └── madsci/           # MADSci custom packages and environment setup scripts
├── assets/           # 3D simulation assets
│   ├── scenes/           # Laboratory layouts
│   ├── architecture/     # Structural elements (walls, floors, ceilings)
│   ├── robots/           # Robot models
│   ├── labware/          # Experimental apparatus (tips, plates, reagents)
│   └── props/            # Any objects for visual/physical flavor
├── src/              # Core implementation source
│   ├── isaacsim/         # Isaac Sim robot control and core simulation scripts
│   └── madsci/           # MADSci robot nodes and config files
└── projects/         # Self-contained experimental projects
    ├── prototyping/      # Development and testing workflows
    └── [custom]          # Any custom workflows
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
