# USD Assets Directory Organization

## Introduction

This document provides a comprehensive guide to organizing and composing USD (Universal Scene Description) assets for laboratory automation scenarios with Isaac Sim integration.

## Core Principles

Our asset organization follows these key principles:
- **Layered composition**: Building complex assets from multiple specialized USD files
- **Separation of concerns**: Isolating geometry, materials, physics, and behavior
- **Traceability**: Maintaining source files for reference and future modifications
- **Consistency**: Following standardized patterns across all asset types
- **Reusability**: Creating modular components that can be composed in multiple ways

## Directory Structure

The assets directory is organized into functional categories:

```
assets/
├── materials/     # Shared material library
├── scenes/        # Laboratory layouts
├── robots/        # Robot models with complete simulation capabilities
├── architecture/  # Structural elements (walls, floors, ceilings)
├── labware/       # Laboratory equipment (plates, tips, reagents)
├── props/         # Environmental objects
└── scripts/       # Scripts used for automation (converting .blend to .usd)

```

### Materials

The shared material library contains commonly used materials that can be referenced across multiple assets. Individual assets can reference these shared materials while also defining asset-specific custom materials when needed.

```
assets/materials/
├── metals/
│   ├── aluminum_anodized.usd
│   ├── steel_brushed.usd
│   └── titanium_matte.usd
├── plastics/
│   ├── abs_black.usd
│   ├── peek_natural.usd
│   └── nylon_white.usd
└── .../
```

### Scenes

The scenes directory contains complete laboratory layouts ready for simulation. These files reference components from the other directories to create fully composed environments.

### Robots

The robots directory contains individual robot definitions. Each robot follows a strict layered composition pattern and presents a single external interface file.

```
assets/robots/picker/
├── source/                    # Original files
│   ├── picker_export.blend    # Main file used to export geo and physics USDs
│   ├── gripper.step
│   ├── base_assembly.stl
│   ├── reference_photos/
│   └── specifications/
├── geometry/
│   └── picker_geo.usd         # Base geometry (Blender USD export)
├── materials/
│   └── picker_materials.usd
├── physics/
│   ├── picker_collision.usd   # Collision shapes (Blender USD export)
│   ├── picker_joints.usd
│   └── picker_physics.usd
├── isaacsim/
│   ├── rmpflow.yaml
│   └── descriptor.yaml
└── picker.usd                 # External interface
```

### Architecture

This directory contains modular building components that can be assembled into different laboratory configurations. Components include walls, floors, ceilings, windows, and other structural elements. Each component follows the same layered approach as Robots but is typically simpler, requiring only geometry, materials, and physics.

### Labware

Laboratory-specific equipment organized by function (tips, plates, reagents, instruments). Follows simpler composition patterns requiring only geometry, materials, and physics.

### Props

Environmental objects that add visual detail or functional elements to scenes but aren't primary simulation objects. Follows simpler composition patterns requiring only geometry, materials, and physics.

### Scripts

Automated processing scripts to quickly convert .blend files into .usd files for geometry or collision shapes, verify relative paths point to valid files, etc.

## Layered Composition Approach

One of USD's most powerful features is its ability to compose scenes from multiple layers. Our system leverages this through a structured approach where each asset is built in distinct layers:

### Robot Composition Chain

Each robot follows a **layered** composition chain that builds from raw geometry to a complete, simulation-ready asset:

**Source files → Geometry → Materials → Physics → Isaac Sim Config → Final Interface**

1. **Source Files**: Original source materials (CAD, Blender, etc.)
2. **Geometry**: Pure mesh data without materials or physics
3. **Materials**: Material assignments added to geometry
4. **Physics**: Collision shapes, joints, and rigid body properties
5. **Isaac Sim Integration**: Configurations for simulation behaviors
6. **External Interface**: The single reference point with variants

### Layer 1: Source Directory

The source directory serves as a permanent archive of all original materials used to create the USD representation. This preserves the origin of all data and enables future modifications from the original sources. The *_export.blend file combines all relevant source material into the final form used to export the geometry and physics USD files in the other layers.

```
source/
├── *_export.blend             # Main Blender file
├── gripper_mechanism.step     # CAD file from manufacturer
├── base_platform.stl          # 3D printed parts
├── wiring_diagram.pdf         # Documentation
├── reference_photos/          # Visual references
└── specifications/            # Technical documentation
```

### Layer 2: Geometry

The geometry layer contains pure mesh data exported from 3D software. This layer contains only geometric definitions. No materials, physics, or behavior.

```usd
# geometry/picker_geo.usd
#usda 1.0
def Xform "Picker"
{
    def Mesh "Body"
    {
        # Raw geometry data only
        point3f[] points = [...]
        int[] faceVertexIndices = [...]
        int[] faceVertexCounts = [...]
    }

    def Mesh "Arm" { ... }
    def Mesh "Gripper" { ... }
}
```

### Layer 3: Materials

The materials layer uses **sublayers** to add material assignments to the base geometry. This layer can reference both shared materials from the global library and asset-specific custom materials. This separation allows materials to be updated independently from geometry.

Asset-specific custom materials:

```
# materials/picker_custom.usd
#usda 1.0
def "Materials"
{
    def Material "SpecialGrip"
    {
        color3f inputs:diffuse_color = (0.2, 0.2, 0.2)
        float inputs:metallic = 0.0
        float inputs:roughness = 0.8
        # Custom material properties specific to this robot
    }
}
```

Composition of materials over the previous layer:

```
# materials/picker_materials.usd
#usda 1.0
(
    sublayers = [
        @../geometry/picker_geo.usd@,
        @./custom_material.usd@,
        @../../../materials/metals/aluminum_anodized.usd@
    ]
)

# Override geometry to add material bindings
over "Picker"
{
    over "Body"
    {
        rel material:binding = </Materials/MetalBody>
    }

    over "Gripper"
    {
        rel material:binding = </Materials/GripperPads>
    }
}

# Define materials
def "Materials"
{
    def Material "MetalBody" { ... }
    def Material "GripperPads" { ... }
}
```

### Layer 4: Physics

The physics layer adds simulation properties such as collision shapes from the source material, joints defined in Isaac Sim, and rigid body definitions.

**Collision Shapes** (exported from source software):
```
# physics/picker_collision.usd
#usda 1.0
def "CollisionShapes"
{
    def Mesh "BodyCollision"
    {
        # Simplified collision geometry (much lower poly than visual mesh)
        point3f[] points = [...]
        # Often basic shapes like boxes, cylinders, spheres
    }

    def Mesh "ArmCollision" { ... }
}
```

Composition of collisions and joints over the previous layer:

```
# physics/picker_physics.usd
#usda 1.0
(
    sublayers = [
        @../materials/picker_materials.usd@,
        @./picker_collision.usd@
    ]
)

# Add physics properties to existing geometry
over "Picker"
{
    # Make the entire robot a rigid body system
    def RigidBodyAPI "RigidBodyAPI"
    {
        bool rigidBodyEnabled = true
    }

    over "Body"
    {
        def CollisionAPI "CollisionAPI"
        {
            bool collisionEnabled = true
            rel physics:collisionMesh = </CollisionShapes/BodyCollision>
        }
    }

    # Joint definitions directly in the physics file
    def RevoluteJoint "ArmJoint"
    {
        rel physics:body0 = </Picker/Body>
        rel physics:body1 = </Picker/Arm>
        point3f physics:localPos0 = (0, 0, 0.2)
        point3f physics:localPos1 = (0, 0, 0)
        vector3f physics:localRot0 = (0, 0, 1)  # Joint axis
        float physics:lowerLimit = -1.57
        float physics:upperLimit = 1.57
    }

    def PrismaticJoint "GripperJoint" { ... }
}
```

### Layer 5: Isaac Sim Integration

This layer contains configuration files specific to Isaac Sim, including motion planning parameters and semantic labels:

```yaml
# isaacsim/rmpflow.yaml - Motion planner configuration
body_collision_controllers:
- name: pointer
  radius: 0.01
canonical_resolve:
  max_acceleration_norm: 50.0
  projection_tolerance: 0.01
# ... additional parameters
```

```yaml
# isaacsim/descriptor.yaml - Robot description
api_version: 1.0
collision_spheres:
- carriage: null
- finger_left: null
# ... collision definitions
```

### Final Layer: External Interface

The external interface is the single file that scenes reference. It includes the complete physics layer and adds variants for different operational states:

```
# picker.usd - Complete external interface
#usda 1.0
def "Picker" (
    references = @./physics/picker_physics.usd@
    variants = {
        string operational_state = "idle"
        string motion_planning = "enabled"
        string lod = "high"
    }
    prepend variantSets = ["operational_state", "motion_planning", "lod"]
)
{
    variantSet "operational_state" = {
        "idle" { ... }
        "picking" { ... }
        "moving" { ... }
        "error" { ... }
    }

    variantSet "motion_planning" = {
        "enabled" {
            # Load motion planning configs
            custom string rmpflow_path = "./isaacsim/rmpflow.yaml"
            custom string descriptor_path = "./isaacsim/descriptor.yaml"
        }
        "disabled" {
            # Robot without motion planning (pure visuals)
        }
    }

    variantSet "lod" = {
        "high" { ... }
        "medium" { ... }
        "low" { ... }
    }
}
```

## Consistent External Interface

All robots, regardless of internal complexity or source, present the same external interface pattern:

```
# In scene files - all robots accessed uniformly
def "Robot001" (
    references = @../../assets/robots/picker/picker.usd@
)
{
    # Set variants for this instance
    string operational_state = "picking"
    string motion_planning = "enabled"
    double3 xformOp:translate = (1.0, 2.0, 0.0)
}
```

## NVIDIA Robot Integration

For integrating NVIDIA's pre-built robots, we maintain our organizational structure while referencing their assets:

```
# carter/carter.usd - Wrapping NVIDIA asset with custom configurations
#usda 1.0
def "Carter" (
    references = </path/to/isaac/assets/carter.usd>
    variants = {
        string navigation_mode = "laboratory"
        string operational_state = "idle"
    }
    prepend variantSets = ["navigation_mode", "operational_state"]
)
{
    # Custom configurations
    variantSet "navigation_mode" = {
        "laboratory" { ... }
        "warehouse" { ... }
    }
}
```

## USD Composition Concepts

Understanding a few key USD concepts will help you work with this organization:

### Sublayers vs. References

- **Sublayers**: Combine multiple USD files into a single layered file. Changes in sublayers affect the composed result.
- **References**: Create instances of existing assets. References maintain their identity and can be overridden.

### Override Operators

The `over` keyword modifies existing prims (USD objects) rather than creating new ones. This allows layers to modify properties of prims defined in earlier layers.

### Variants

Variants allow different configurations of the same asset. They're ideal for:
- Different operational states (idle, working, error)
- Level of detail settings
- Feature toggles (motion planning on/off)
