from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

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
    microplate_asset_path = CUSTOM_ASSETS_ROOT_PATH + "/labware/microplate/microplate.usd"
    add_reference_to_stage(
        usd_path=microplate_asset_path,
        prim_path="/World/microplate",
    )
    microplate_prim = world.stage.GetPrimAtPath("/World/microplate")
    utils.set_prim_world_pose(microplate_prim, position=np.array([0.3, 0.3, 0.3]))

    # Enable collision detection for microplate
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(microplate_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)

    platform1_prim = create_prim(
        prim_path="/World/platform1",
        prim_type="Cube",
        position=np.array([0.73, 0.75, -0.205]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    platform2_prim = create_prim(
        prim_path="/World/platform2",
        prim_type="Cube",
        position=np.array([0.73, -0.75, -0.205]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    # Add colliders to all cubes using the utility function
    utils.add_collider_to_prim(platform1_prim)
    utils.add_collider_to_prim(platform2_prim)

    # Create reference position markers (invisible Xforms for coordinate calculation)
    create_prim(
        prim_path="/World/high",
        prim_type="Xform",
        position=np.array([0.245, 0.0, 1.043]),
    )

    # Platform1 dropoff position at (0.3, 0.3, 0.3) - above platform1
    create_prim(
        prim_path="/World/platform1_dropoff",
        prim_type="Xform",
        position=np.array([0.3, 0.3, 0.3]),
    )

    # Platform2 dropoff position at (0.3, -0.3, 0.3) - above platform2
    create_prim(
        prim_path="/World/platform2_dropoff",
        prim_type="Xform",
        position=np.array([0.3, -0.3, 0.3]),
    )

    # Approach position for safe movements
    create_prim(
        prim_path="/World/approach",
        prim_type="Xform",
        position=np.array([0.4, 0.4, 0.5]),
    )


def main():
    # Create world
    world = World(stage_units_in_meters=1.0)

    # Create scene objects (including microplates and platforms)
    create_scene_objects(world)

    # Robot configuration
    robots_config = [
        # {
        #     "name": "ur5e_1",
        #     "type": "ur5e",
        #     "port": 5555,
        #     "asset_path": NVIDIA_ASSETS_ROOT_PATH + "/robots/UniversalRobots/ur5e/ur5e.usd",
        #     "position": [2.0, 0.0, 0.0],
        #     "orientation": [1.0, 0.0, 0.0, 0.0],
        # },
        {
            "name": "pf400_1",
            "type": "pf400",
            "port": 5557,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Brooks/PF400/PF400.usd",
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        },
        {
            "name": "ot2_1",
            "type": "ot2",
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/robots/Opentrons/OT-2/OT-2.usd",
            "position": [0.0, 2.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
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
