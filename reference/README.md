# Reference Material

This directory contains reference codebases and libraries from MADSci, organized as git submodules.

## MADSci Core Framework

### MADSci_Core/
The main MADSci (Modular Autonomous Discovery for Science) framework - a modular, autonomous, and scalable toolkit for scientific discovery and experimentation. Provides:
- Laboratory instrument automation and integration via the MADSci Node standard
- Workflow management for flexible scientific workflows
- Experiment management for closed-loop autonomous experiments
- Resource, event, and data management systems

### MADSci_Examples/
Tutorial notebooks and examples demonstrating MADSci core concepts:
- Node integration examples for device automation
- Experiment application development guides
- Hands-on tutorials for building autonomous laboratories

## MADSci Device Modules

The `MADSci_Modules/` directory contains individual device integration modules that implement the MADSci Node standard. Each module provides a standardized REST API interface for laboratory equipment:

## Usage

These submodules are used as reference for:
- Understanding MADSci Node interfaces and protocols
- Implementing custom integrations with Isaac Sim
- Building experimental workflows that leverage existing device modules
- Learning from real-world autonomous laboratory implementations

To update all submodules to their latest versions:
```bash
git submodule update --remote --recursive
```