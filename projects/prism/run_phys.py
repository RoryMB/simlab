"""Isaac Sim entry point for prism project using ROUTER-DEALER ZMQ pattern."""

from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})


import numpy as np

from isaacsim.core.api import World
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.prims import create_prim
from pxr import PhysxSchema

from slcore.common import utils
from slcore.common.primary_functions import create_parallel_robots, CollisionDetector, CUSTOM_ASSETS_ROOT_PATH
from slcore.common.parallel_config import ParallelConfig
from slcore.robots.common.config import DEFAULT_PHYSICS_CONFIG


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
    utils.set_xform_world_pose(microplate_prim, np.array([0.80263, -0.37815, 0.27746]), np.array([1.0, 0.0, 0.0, 0.0]))

    # Enable collision detection for microplate
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(microplate_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)

    # Set contact offset for microplate
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(microplate_prim)
    physx_collision_api.CreateContactOffsetAttr().Set(DEFAULT_PHYSICS_CONFIG.contact_offset)

    exchange_deck = create_prim(
        prim_path="/World/env_0/exchange_deck",
        prim_type="Cube",
        position=np.array([1.07, 0.75, -0.23]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    utils.add_collider_to_prim(exchange_deck)
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(exchange_deck)
    physx_collision_api.CreateContactOffsetAttr().Set(DEFAULT_PHYSICS_CONFIG.contact_offset)

    # Create reference position markers (invisible Xforms for coordinate calculation)
    create_prim(
        prim_path="/World/env_0/target",
        prim_type="Xform",
        position=np.array([0.0, 0.0, 1.0]),
    )

    # PF400 location markers (from captured EE world poses)
    # These allow goto_prim to move the end effector to these world positions
    # Each location has a main position and a hover position (0.1m above for safe approach)
    HOVER_HEIGHT = 0.1

    pf400_locations = {
        # Home position (reset state)
        "home": {
            "position": [0.0, 0.0, 0.5],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        # OT-2 locations
        "safe_path_ot2bioalpha": {
            "position": [0.803, 0.0, 0.474],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        "ot2bioalpha_deck1_wide": {
            "position": [0.803, -0.378, 0.283],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        # Exchange deck locations
        "safe_path_exchange": {
            "position": [0.640, 0.300, 0.574],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        "exchange_deck_high_wide": {
            "position": [0.640, 0.300, 0.296],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
        "exchange_deck_high_narrow": {
            "position": [0.640, 0.300, 0.276],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        # Sealer locations
        "safe_path_sealer": {
            "position": [0.061, -0.307, 0.548],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        "sealer_nest": {
            "position": [0.060, -0.307, 0.269],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        # Thermocycler locations (calibrated from joint angles)
        "safe_path_biometra3": {
            "position": [0.161, 0.387, 0.590],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
        "bio_biometra3_nest": {
            "position": [0.161, 0.387, 0.333],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
        # Peeler locations (calibrated from joint angles)
        "safe_path_peeler": {
            "position": [-0.284, -0.342, 0.568],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        "peeler_nest": {
            "position": [-0.285, -0.342, 0.269],
            "orientation": [-0.707, 0.0, 0.0, 0.707],
        },
        # Hidex locations (calibrated from joint angles)
        "safe_path_hidex": {
            "position": [-0.279, 0.0, 0.408],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        "hidex_geraldine_high_nest": {
            "position": [-0.401, 0.229, 0.210],
            "orientation": [0.707, 0.0, 0.0, 0.707],
        },
    }

    for name, pose in pf400_locations.items():
        # Create main location marker
        create_prim(
            prim_path=f"/World/env_0/locations/{name}",
            prim_type="Xform",
            position=np.array(pose["position"]),
            orientation=np.array(pose["orientation"]),
        )
        # Create hover marker (same position but higher z)
        hover_pos = pose["position"].copy() if isinstance(pose["position"], list) else list(pose["position"])
        hover_pos[2] += HOVER_HEIGHT
        create_prim(
            prim_path=f"/World/env_0/locations/{name}_hover",
            prim_type="Xform",
            position=np.array(hover_pos),
            orientation=np.array(pose["orientation"]),
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

    # Robot configuration (base robots without env_id or prim_path - these are auto-generated)
    base_robots_config = [
        {
            "type": "ot2",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Opentrons/OT-2/OT-2.usd"),
            "position": [0.67, -0.55, 0.2],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "pf400",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Brooks/PF400/PF400.usd"),
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "type": "sealer",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Azenta/a4SSealer/a4SSealer.usd"),
            "position": [0.06, -0.675, 0.125],
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
        {
            "type": "hidex",
            "asset_path": str(CUSTOM_ASSETS_ROOT_PATH / "robots/Hidex/SenseMicroplateReader/SenseMicroplateReader.usd"),
            "position": [-0.4, 0.55, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
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

    # Set up collision detection (MUST be after world.reset())
    collision_detector = CollisionDetector(handlers)

    # Start ZMQ ROUTER server
    router_server.start_server()

    print(f"\nPrism project running with {len(handlers)} robots")
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
