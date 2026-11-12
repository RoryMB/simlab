# USD Assets Directory Organization

## Introduction

This directory holds the USD (Universal Scene Description) assets used by the laboratory automation simulations in Isaac Sim, together with the source files they are built from.

## Core Principles

- **Meshes live in Blender exports**: All mesh data sits in binary geometry files exported from Blender. Everything added on top (materials, physics, joints) sits in a small text file that overrides the geometry. A mesh can be re-exported without disturbing the rest, and the text file stays small enough to read in full.
- **Traceability**: Each asset keeps its source files (CAD, reference photos, the Blender file).
- **Consistency**: Every asset follows the same layout and naming.
- **Reusability**: Materials used by more than one asset live in one shared library.

## Directory Structure

```
assets/
├── materials/     # Shared material library
├── scenes/        # Laboratory layouts
├── robots/        # Robot models with complete simulation capabilities
├── architecture/  # Structural elements (walls, floors, ceilings)
├── labware/       # Laboratory equipment (plates, tips, reagents)
├── props/         # Environmental objects
└── tools/         # Scripts for inspecting how USD files compose
```

### File Extensions

The extension tells you what role a USD file plays:

- `.usd`: a top-level asset file, the one you load or reference from a scene (for example `picker.usd`). These sit directly in the asset's directory.
- `.usda`: a text layer underneath a top-level file, such as a material. These are meant to be read and edited as text.
- `.usdc`: geometry exported from Blender. Change these by re-exporting from the source `.blend` (see [Exporting Geometry from Blender](#exporting-geometry-from-blender)), never by editing them.

USD reads both text and binary content under `.usd`, so a top-level file can be either.

### Materials

The shared material library holds materials used by more than one asset. A material used by only one asset lives in that asset's own `materials/` directory instead.

```
assets/materials/
├── black_glossy.usda
├── glass.usda
├── metal.usda
├── transparent_plastic.usda
├── vention_bar.usda
└── ...
```

### Scenes

The scenes directory contains complete laboratory layouts ready for simulation. These files reference assets from the other directories.

### Robots

Each robot directory follows this layout:

```
assets/robots/picker/
├── source/                    # Original files
│   ├── picker_export.blend    # Blender file the geometry is exported from
│   ├── gripper.step           # CAD from the manufacturer
│   ├── reference_photos/
│   └── notes.txt
├── geometry/
│   └── picker.usdc            # Mesh data exported from picker_export.blend
├── materials/
│   └── gripper_pad.usda       # Materials only this asset uses
├── isaacsim/                  # Configuration loaded by robot control code
│   ├── picker.urdf
│   ├── descriptor.yaml
│   └── rmpflow.yaml
└── picker.usd                 # Top-level asset file
```

**Naming Convention:** Asset directories use original manufacturer and product names (e.g., `Opentrons/OT-2`, `Brooks/PF400`) for traceability to official documentation. Code in `slcore/robots/` uses lowercase identifiers (e.g., `ot2`, `pf400`) per Python naming conventions (PEP 8). Within an asset directory, files are named after the asset: `<Name>.usd`, `geometry/<Name>.usdc`, `source/<Name>_export.blend`, and `isaacsim/<Name>.urdf`. The other files in `isaacsim/` keep the fixed names robot control code loads them by, such as `descriptor.yaml` and `rmpflow.yaml`. A directory can hold several closely related assets, such as the three lab table variants in `architecture/lab_table/`, each with its own set of files.

### Architecture, Labware, and Props

These follow the same layout as robots, usually without `isaacsim/`:

- **Architecture**: structural elements such as rooms, tables, and carts.
- **Labware**: laboratory consumables and equipment such as plates and tips.
- **Props**: environmental objects that add visual detail to scenes but aren't primary simulation objects.

## How an Asset Is Composed

A top-level asset file lists its layers as sublayers, strongest first: the asset's own materials, the shared materials it uses, and its geometry. Everything else in the file overrides prims the geometry defines (material bindings, rigid bodies, colliders, joints, drives, and visibility), or defines prims that exist only in Isaac Sim, such as joints and lights.

```
# picker.usd
#usda 1.0
(
    defaultPrim = "World"
    subLayers = [
        @materials/gripper_pad.usda@,
        @../../materials/metal.usda@,
        @geometry/picker.usdc@
    ]
)

over "World" (
    prepend apiSchemas = ["PhysicsArticulationRootAPI"]
)
{
    over "base" (
        prepend apiSchemas = ["PhysicsRigidBodyAPI"]
    )
    {
        over "base_mesh" (
            prepend apiSchemas = ["PhysicsCollisionAPI"]
        )
        {
            rel material:binding = </World/Looks/common/metal>
        }

        def PhysicsRevoluteJoint "arm_joint" { ... }
    }
}
```

Projects load an asset with `add_reference_to_stage`, which brings in the file's default prim, `World`. Anything outside `World` never reaches a project scene.

### Rules for Editing Assets

- **Change meshes and their hierarchy in Blender, then re-export.** Don't move, rename, or reparent geometry prims in Isaac Sim. Isaac Sim can't move a prim that a sublayer defines, so it copies the whole mesh into the top-level file and deactivates the original. From then on, edits in Blender no longer show up.
- **Keep Blender object names stable.** Overrides attach to geometry by prim path, so a renamed or reparented object silently loses its materials and physics. After re-exporting, run the check in [Checking Overrides After an Export](#checking-overrides-after-an-export).
- **Don't keep PhysX cooked collision data in asset files.** These are the `physxCookedData*` attributes and `PhysxCookedDataAPI` schemas. They're a cache Isaac Sim rebuilds when it loads an asset, and they can add tens of megabytes to a file. If saving from Isaac Sim writes them back, remove them.
- **Don't add a viewing environment (ground plane, lights) to asset files.** Put it in a scene instead.

## Isaac Sim Integration

The `isaacsim/` directory holds the configuration that robot control code loads by path, such as the URDF, the motion planner configuration, and the robot description. Robots with differential IK also have `motion_config.yaml` and `differential_ik_config.yaml`; see `robots/Brooks/PF400/isaacsim/`.

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

## Inspection Tools

`tools/` holds scripts for inspecting assets without reading the files. Each script's `--help` lists its options.

- `show_composition.py`: the tree of sublayers, references, and payloads a file pulls in; `--check` only reports missing files.
- `layer_diff.py`: what a single layer defines (`def`) versus overrides (`over`), and the files it references.
- `find_prim_source.py`: every layer that contributes to one prim.
- `find_deactivated.py`: prims switched off with `active = false`. An unexpected one in a top-level file is often a geometry prim Isaac Sim copied when it was moved.
- `list_prims.py`: lists prims under a path, by name, by type, or with duplicated names.

## Exporting Geometry from Blender

Use Blender 5.2. Other versions triangulate and compute normals differently, so exporting with them changes the geometry even when the `.blend` is untouched. The `.blend` files are saved in Blender 5.2's format, which older versions can't open.

The export script below does the following, without saving anything back to the `.blend`:

1. Parents every root object under an empty named `World`, creating it if needed, while keeping each object where it is. All prims then land under `/World`.
2. Adds a Triangulate modifier (Beauty quad method) to each visible mesh, curve, surface, and text object. It goes just before any "Auto Smooth" or "Smooth by Angle" modifier, so normals are computed on the triangulated mesh.
3. Names each object's mesh data `<object>_mesh`, which becomes the mesh prim's name.
4. Exports those objects with matrix transforms, the original UV map names, no root prim, and no Blender metadata, lights, or cameras.
5. Removes Blender's internal attributes (primvars starting with `__`), makes `/World` the default prim, and gives `/World` identity translate, orient, and scale ops.

Save the script outside the repository, for example as `/tmp/export_usd.py`:

```python
"""Export the open .blend's geometry to the .usdc path after `--`. Nothing is saved back to the .blend."""
import sys
import bpy
from pxr import Gf, Sdf, Usd, Vt

out = sys.argv[sys.argv.index("--") + 1]
GEOMETRY_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}
MODIFIABLE_TYPES = {"MESH", "CURVE", "SURFACE", "FONT"}

if bpy.context.active_object is not None:
    bpy.ops.object.mode_set(mode="OBJECT")
scene = bpy.context.scene

# Every asset's prims live under /World, which becomes the layer's default prim.
world = bpy.data.objects.get("World")
if world is None:
    world = bpy.data.objects.new("World", None)
    scene.collection.objects.link(world)
for obj in scene.objects:
    if obj is not world and obj.parent is None:
        mw = obj.matrix_world.copy()
        obj.parent = world
        obj.matrix_world = mw

bpy.ops.object.select_all(action="DESELECT")
for obj in scene.objects:
    if obj.type not in GEOMETRY_TYPES or not obj.visible_get():
        continue
    if obj.type in MODIFIABLE_TYPES:
        tri = obj.modifiers.new("Triangulate", "TRIANGULATE")
        tri.quad_method = "BEAUTY"
        # Smoothing modifiers compute normals from the mesh they receive, so triangulate just before them.
        smooth = [i for i, m in enumerate(obj.modifiers)
                  if m.type == "NODES" and m.node_group is not None
                  and m.node_group.name.startswith(("Auto Smooth", "Smooth by Angle"))]
        if smooth:
            obj.modifiers.move(len(obj.modifiers) - 1, smooth[0])
    obj.data.name = obj.name + "_mesh"
    obj.select_set(True)

bpy.ops.wm.usd_export(
    filepath=out, check_existing=False, selected_objects_only=True,
    export_animation=False, export_hair=False,
    export_uvmaps=True, rename_uvmaps=False, export_mesh_colors=False, export_normals=True,
    export_materials=True, generate_preview_surface=False, generate_materialx_network=False,
    use_instancing=True, relative_paths=True,
    xform_op_mode="MAT", root_prim_path="", allow_unicode=False,
    export_custom_properties=False, author_blender_name=False, convert_world_material=False,
    export_lights=False, export_cameras=False,
)

stage = Usd.Stage.Open(out)
# Blender exports its internal attributes (names starting with "__", such as modifier scratch data) as primvars.
for prim in stage.Traverse():
    for attr in prim.GetAttributes():
        if attr.GetName().startswith("primvars:__"):
            prim.RemoveProperty(attr.GetName())
world_prim = stage.GetPrimAtPath("/World")
stage.SetDefaultPrim(world_prim)
world_prim.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(0, 0, 0))
world_prim.CreateAttribute("xformOp:orient", Sdf.ValueTypeNames.Quatd).Set(Gf.Quatd(1, 0, 0, 0))
world_prim.CreateAttribute("xformOp:scale", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(1, 1, 1))
world_prim.CreateAttribute("xformOpOrder", Sdf.ValueTypeNames.TokenArray).Set(
    Vt.TokenArray(["xformOp:translate", "xformOp:orient", "xformOp:scale"]))
stage.Save()
print("EXPORTED", out)
```

Export one asset, running from `assets/`:

```bash
blender -b --factory-startup \
    robots/Brooks/PF400/source/PF400_export.blend \
    --python /tmp/export_usd.py -- robots/Brooks/PF400/geometry/PF400.usdc
```

Each export is independent, so export several assets by running Blender processes in parallel:

```bash
find . -name '*_export.blend' | xargs -n 1 -P 6 sh -c '
    blend="$1"; asset="${blend%/source/*}"; name="$(basename "$blend" _export.blend)"
    blender -b --factory-startup "$blend" \
        --python /tmp/export_usd.py -- "$asset/geometry/$name.usdc" > "/tmp/export_$name.log" 2>&1 \
        || echo "FAILED: $blend"' _
```

### Checking Overrides After an Export

Every prim a top-level file overrides must still exist after an export. A prim that's overridden but no longer defined anywhere means an object was renamed or moved in Blender. This lists any such prims, run from the repository root:

```bash
python -c '
from pxr import Usd
stage = Usd.Stage.Open("assets/robots/Brooks/PF400/PF400.usd")
for prim in stage.TraverseAll():
    if not prim.IsDefined():
        print("override on missing prim:", prim.GetPath())'
```

## Planned: Wrapping Isaac Sim Robots

Not implemented yet. A robot that Isaac Sim provides, such as the UR5e meant to replace `robots/UniversalRobots/ur5e/`, is to get its own directory here, with a top-level file that references the Isaac Sim asset and adds any overrides. Projects then load it the same way as every other asset. Where the reference points depends on where Isaac Sim's assets are installed, which is still to be settled.

```
# robots/UniversalRobots/ur5e/ur5e.usd
#usda 1.0
(
    defaultPrim = "World"
)

def Xform "World" (
    references = @<path to the Isaac Sim UR5e asset>@
)
{
    # Overrides on the Isaac Sim robot, such as material bindings or drive settings
}
```

## USD Composition Concepts

Understanding a few key USD concepts will help you work with this organization:

### Sublayers vs. References

- **Sublayers**: Combine multiple USD files into a single layered file. Changes in sublayers affect the composed result.
- **References**: Create instances of existing assets. References maintain their identity and can be overridden.

### Override Operators

The `over` keyword modifies existing prims (USD objects) rather than creating new ones. This allows layers to modify properties of prims defined in earlier layers.
