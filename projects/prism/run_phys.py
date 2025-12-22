from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "../../src/isaacsim"))

import numpy as np

from isaacsim.core.api import World
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.prims import create_prim
from pxr import PhysxSchema

import utils
from primary_functions import create_robot, CollisionDetector, CUSTOM_ASSETS_ROOT_PATH


def create_scene_objects(world):
    """Create scene objects"""

    # Add default ground plane
    world.scene.add_default_ground_plane()

    # Create microplate at position (0.3, 0.3, 0.3)
    microplate_asset_path = CUSTOM_ASSETS_ROOT_PATH + "/temp/objects/microplate.usda"
    add_reference_to_stage(
        usd_path=microplate_asset_path,
        prim_path="/World/microplate",
    )
    microplate_prim = world.stage.GetPrimAtPath("/World/microplate")
    # utils.set_prim_world_pose(microplate_prim, position=np.array([0.64, 0.5, 0.3]))
    utils.set_prim_world_pose(microplate_prim, position=np.array([0.80263, -0.37815, 0.27746]))

    # Enable collision detection for microplate
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(microplate_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)

    # Set contact offset for microplate
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(microplate_prim)
    physx_collision_api.CreateContactOffsetAttr().Set(0.0)

    exchange_deck = create_prim(
        prim_path="/World/exchange_deck",
        prim_type="Cube",
        position=np.array([1.07, 0.75, -0.23]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    utils.add_collider_to_prim(exchange_deck)
    physx_collision_api = PhysxSchema.PhysxCollisionAPI.Apply(exchange_deck)
    physx_collision_api.CreateContactOffsetAttr().Set(0.0)

    # Create reference position markers (invisible Xforms for coordinate calculation)
    create_prim(
        prim_path="/World/target",
        prim_type="Xform",
        position=np.array([0.0, 0.0, 1.0]),
    )

def main():
    # Create world
    world = World(stage_units_in_meters=1.0)

    # Create scene objects (including microplates and platforms)
    create_scene_objects(world)

    # Robot configuration
    robots_config = [
        {
            "prim_path": "/World/ot2_0",
            "name": "ot2_0",
            "type": "ot2",
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/ot2.usda",
            "position": [0.67, -0.55, 0.2],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "prim_path": "/World/pf400_0",
            "name": "pf400_0",
            "type": "pf400",
            "port": 5557,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/pf400.usda",
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },

        {
            "prim_path": "/World/sealer_0",
            "name": "sealer_0",
            "type": "sealer",
            "port": 5558,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/sealer.usda",
            "position": [0.06, -0.675, 0.125],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "prim_path": "/World/peeler_0",
            "name": "peeler_0",
            "type": "peeler",
            "port": 5559,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/peeler.usda",
            "position": [-0.4, -0.625, 0.125],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "prim_path": "/World/thermocycler_0",
            "name": "thermocycler_0",
            "type": "thermocycler",
            "port": 5560,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/thermocycler.usda",
            "position": [0.16, 0.4, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
        },
        {
            "prim_path": "/World/hidex_0",
            "name": "hidex_0",
            "type": "hidex",
            "port": 5561,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/hidex.usda",
            "position": [-0.4, 0.55, 0.125],
            "orientation": [0.0, 0.0, 0.0, 1.0],
        },
    ]

    # Create robots and their ZMQ servers
    zmq_servers = {}
    for config in robots_config:
        robot, zmq_server = create_robot(simulation_app, world, config)
        zmq_servers[config["name"]] = zmq_server

    # Reset world to initialize physics
    world.reset()

    # Set up collision detection (MUST be after world.reset())
    _collision_detector = CollisionDetector(zmq_servers)

    # Start all ZMQ servers
    for server in zmq_servers.values():
        server.start_server()

    # Run simulation loop
    try:
        while simulation_app.is_running():
            # Call robot server update methods each frame
            for server in zmq_servers.values():
                if hasattr(server, 'update'):
                    server.update()

            # Step the simulation
            world.step(render=True)
    except KeyboardInterrupt:
        pass

    simulation_app.close()

if __name__ == "__main__":
    main()
