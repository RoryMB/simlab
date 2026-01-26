"""Isaac Sim entry point template using ROUTER-DEALER ZMQ pattern."""

from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import numpy as np

from isaacsim.core.api import World
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.prims import create_prim

from slcore.common import utils
from slcore.common.primary_functions import create_parallel_robots, CollisionDetector, CUSTOM_ASSETS_ROOT_PATH
from slcore.common.parallel_config import ParallelConfig


def create_scene_objects(world):
    """Create scene objects"""

    # Add default ground plane
    world.scene.add_default_ground_plane()

    # Create microplate at position (0.3, 0.3, 0.3)
    microplate_asset_path = str(CUSTOM_ASSETS_ROOT_PATH / "labware/microplate/microplate.usd")
    add_reference_to_stage(
        usd_path=microplate_asset_path,
        prim_path="/World/env_0/microplate",
    )
    microplate_prim = world.stage.GetPrimAtPath("/World/env_0/microplate")
    utils.set_xform_world_pose(microplate_prim, np.array([0.3, 0.3, 0.3]), np.array([1.0, 0.0, 0.0, 0.0]))

    platform1_prim = create_prim(
        prim_path="/World/env_0/platform1",
        prim_type="Cube",
        position=np.array([0.73, 0.75, -0.205]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    platform2_prim = create_prim(
        prim_path="/World/env_0/platform2",
        prim_type="Cube",
        position=np.array([0.73, -0.75, -0.205]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    # Add colliders to all cubes using the utility function
    utils.add_collider_to_prim(platform1_prim)
    utils.add_collider_to_prim(platform2_prim)

    # Create reference position markers (invisible Xforms for coordinate calculation)
    create_prim(
        prim_path="/World/env_0/locations/high",
        prim_type="Xform",
        position=np.array([0.245, 0.0, 1.043]),
    )

    # Platform1 dropoff position at (0.3, 0.3, 0.3) - above platform1
    create_prim(
        prim_path="/World/env_0/locations/platform1_dropoff",
        prim_type="Xform",
        position=np.array([0.3, 0.3, 0.3]),
    )

    # Platform2 dropoff position at (0.3, -0.3, 0.3) - above platform2
    create_prim(
        prim_path="/World/env_0/locations/platform2_dropoff",
        prim_type="Xform",
        position=np.array([0.3, -0.3, 0.3]),
    )

    # Approach position for safe movements
    create_prim(
        prim_path="/World/env_0/locations/approach",
        prim_type="Xform",
        position=np.array([0.4, 0.4, 0.5]),
    )


def main():
    # Create world
    world = World(stage_units_in_meters=1.0)

    # Create scene objects (including microplates and platforms)
    create_scene_objects(world)

    # Single environment configuration
    parallel_config = ParallelConfig(
        num_envs=1,
        spacing=0.0,
        zmq_port=5555,
    )

    # Robot configuration
    base_robots_config = [
        {
            "type": "pf400",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Brooks/PF400/PF400.usd"),
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "ot2",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Opentrons/OT-2/OT-2.usd"),
            "position": [0.0, 2.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
    ]

    # Create robots and ZMQ ROUTER server
    router_server, handlers = create_parallel_robots(
        simulation_app,
        world,
        base_robots_config,
        parallel_config,
    )

    # Reset world to initialize physics
    world.reset()

    # Set up collision detection
    collision_detector = CollisionDetector(handlers)

    # Start ZMQ ROUTER server
    router_server.start_server()

    print(f"\nTemplate project running with {len(handlers)} robots")
    print(f"ZMQ ROUTER server listening on port {parallel_config.zmq_port}")
    print("Press Ctrl+C to stop\n")

    # Run simulation loop
    try:
        while simulation_app.is_running():
            # Call robot handler update methods each frame
            for handler in handlers.values():
                handler.update()

            # Step the simulation
            world.step(render=True)
    except KeyboardInterrupt:
        print("\nShutting down...")

    simulation_app.close()

if __name__ == "__main__":
    main()
