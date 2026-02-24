"""Isaac Sim entry point for the simple project with a single environment."""

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.utils.prims import create_prim
from isaacsim.core.utils.stage import add_reference_to_stage
from pxr import PhysxSchema

from slcore.common import utils
from slcore.common.primary_functions import create_parallel_robots, CollisionDetector, CUSTOM_ASSETS_ROOT_PATH
from slcore.common.parallel_config import ParallelConfig
from slcore.robots.common.config import DEFAULT_PHYSICS_CONFIG


# PF400 location markers for workflow execution
# These are world coordinates where the PF400 end effector should move to.
# Each location has a hover position above it for safe vertical approach.
HOVER_HEIGHT = 0.1  # 10cm above target

PF400_LOCATIONS = {
    "home": {
        "position": [0.0, 0.0, 0.5],
        "orientation": [1.0, 0.0, 0.0, 0.0],
    },
    "staging": {
        "position": [0.3, 0.0, 0.3],
        "orientation": [1.0, 0.0, 0.0, 0.0],
    },
    "thermocycler_nest": {
        "position": [0.161, 0.387, 0.333],
        "orientation": [0.707, 0.0, 0.0, 0.707],
    },
    "peeler_nest": {
        "position": [-0.285, -0.342, 0.299],
        "orientation": [-0.707, 0.0, 0.0, 0.707],
    },
}


def create_location_markers():
    """Create PF400 location xform markers in the scene.

    These invisible markers let the PF400 use goto_prim to move
    to named positions (e.g., /World/env_0/locations/home).
    """
    for name, pose in PF400_LOCATIONS.items():
        pos = np.array(pose["position"])
        orient = np.array(pose["orientation"])

        create_prim(
            prim_path=f"/World/env_0/locations/{name}",
            prim_type="Xform",
            position=pos,
            orientation=orient,
        )

        hover_pos = pos.copy()
        hover_pos[2] += HOVER_HEIGHT
        create_prim(
            prim_path=f"/World/env_0/locations/{name}_hover",
            prim_type="Xform",
            position=hover_pos,
            orientation=orient,
        )


def create_microplate(world):
    """Create a microplate at the peeler nest for transfer testing."""
    microplate_asset_path = str(CUSTOM_ASSETS_ROOT_PATH / "labware/microplate/microplate.usd")
    prim_path = "/World/env_0/microplate"

    add_reference_to_stage(
        usd_path=microplate_asset_path,
        prim_path=prim_path,
    )

    # Position at peeler nest (peeler is open, thermocycler starts closed)
    plate_pos = np.array(PF400_LOCATIONS["peeler_nest"]["position"])
    plate_rot = np.array([1.0, 0.0, 0.0, 0.0])

    microplate_prim = world.stage.GetPrimAtPath(prim_path)
    utils.set_xform_world_pose(microplate_prim, plate_pos, plate_rot)

    # Enable collision detection
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(microplate_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(microplate_prim)
    physx_collision_api.CreateContactOffsetAttr().Set(DEFAULT_PHYSICS_CONFIG.contact_offset)


def main():
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    # Single environment
    parallel_config = ParallelConfig(
        num_envs=1,
        spacing=0.0,
        zmq_port=5555,
    )

    # Robots: PF400 arm, peeler, and thermocycler
    base_robots_config = [
        {
            "type": "pf400",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Brooks/PF400/PF400.usd"),
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "peeler",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Azenta/XPeel/XPeel.usd"),
            "position": [-0.4, -0.625, 0.125],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "thermocycler",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/AnalytikJena/Biometra/Biometra.usd"),
            "position": [0.16, 0.4, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
        },
    ]

    router_server, handlers = create_parallel_robots(
        simulation_app,
        world,
        base_robots_config,
        parallel_config,
    )

    create_location_markers()
    create_microplate(world)

    world.reset()

    collision_detector = CollisionDetector(handlers)
    router_server.start_server()

    print("Simulation App Startup Complete")
    print(f"\nSimple project: 1 environment with {len(handlers)} robots")
    print(f"ZMQ ROUTER server listening on port {parallel_config.zmq_port}")
    print("\nPress Ctrl+C to stop\n")

    try:
        while simulation_app.is_running():
            for handler in handlers.values():
                handler.update()
            world.step(render=True)
    except KeyboardInterrupt:
        print("\nShutting down...")

    simulation_app.close()


if __name__ == "__main__":
    main()
