# Reference Material

This directory contains reference codebases and libraries from MADSci.
These should not be linked to from project code, and are just provided as a reference and guide to base your own code on.

## MADSci/
The main MADSci (Modular Autonomous Discovery for Science) framework - a modular, autonomous, and scalable toolkit for scientific discovery and experimentation. Provides:
- Laboratory instrument automation and integration via the MADSci Node standard
- Workflow management for flexible scientific workflows
- Experiment management for closed-loop autonomous experiments
- Resource, event, and data management systems

## MADSci_Examples/
Tutorial notebooks and examples demonstrating MADSci core concepts

## MADSci_Labs
Labs using MADSci, with node and workcell files specific to each lab space

## MADSci_Experiments
Experiments demonstrating how to use MADSci components like:
- Experiment "app" python scripts, which guide the full execution of an experiment
- Workflows, which are submitted to run by the app
- Protocols that run on the OT-2 liquid handler

## MADSci_Modules

The `MADSci_Modules/` directory contains individual device integration modules that implement the MADSci Node standard.
Each module provides a standardized REST API interface for laboratory equipment.
