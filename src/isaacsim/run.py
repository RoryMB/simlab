from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import sys
from pathlib import Path
import numpy as np

from isaacsim.core.api import World
from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.prims import create_prim
from isaacsim.storage.native import get_assets_root_path

import utils
from zmq_ot2_server import ZMQ_OT2_Server
from zmq_ur5e_server import ZMQ_UR5e_Server
from zmq_pf400_server import ZMQ_PF400_Server


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())

NVIDIA_ASSETS_ROOT_PATH = get_assets_root_path()
if NVIDIA_ASSETS_ROOT_PATH is None:
    print("Error: Could not find Isaac Sim assets folder")
    simulation_app.close()
    sys.exit()


def create_robots(world, robots_config):
    """Create robots and their ZMQ servers"""
    robots = []
    zmq_servers = []

    for config in robots_config:
        # Create robot in simulation
        add_reference_to_stage(
            usd_path=config["asset_path"],
            prim_path=f"/World/{config['name']}",
        )
        if "position" in config or "orientation" in config:
            robot_prim = world.stage.GetPrimAtPath(f"/World/{config['name']}")

            position = np.array(config.get("position", [0.0, 0.0, 0.0]))
            orientation = np.array(config.get("orientation", [1.0, 0.0, 0.0, 0.0]))

            utils.set_prim_world_pose(robot_prim, position=position, orientation=orientation)

        robot = world.scene.add(Robot(
            prim_path=f"/World/{config['name']}",
            name=config["name"],
        ))

        # Create appropriate ZMQ server based on robot type
        robot_type = config.get("type", "generic")
        motion_type = config.get("motion_type", "teleport")

        if robot_type == "ot2":
            zmq_server = ZMQ_OT2_Server(simulation_app, robot, config["name"], config["port"], motion_type)
        elif robot_type == "pf400":
            zmq_server = ZMQ_PF400_Server(simulation_app, robot, config["name"], config["port"], motion_type)
        else:
            # Default to generic robot server (for UR5e, etc.)
            zmq_server = ZMQ_UR5e_Server(simulation_app, robot, config["name"], config["port"], motion_type)

        robots.append(robot)
        zmq_servers.append(zmq_server)

    return robots, zmq_servers


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
    utils.set_prim_world_pose(microplate_prim, position=np.array([0.3, 0.3, 0.3]))

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
    high_prim = create_prim(
        prim_path="/World/high",
        prim_type="Xform",
        position=np.array([0.245, 0.0, 1.043]),
    )

    # Platform1 dropoff position at (0.3, 0.3, 0.3) - above platform1
    platform1_dropoff_prim = create_prim(
        prim_path="/World/platform1_dropoff",
        prim_type="Xform",
        position=np.array([0.3, 0.3, 0.3]),
    )

    # Platform2 dropoff position at (0.3, -0.3, 0.3) - above platform2
    platform2_dropoff_prim = create_prim(
        prim_path="/World/platform2_dropoff",
        prim_type="Xform",
        position=np.array([0.3, -0.3, 0.3]),
    )

    # Approach position for safe movements
    approach_prim = create_prim(
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
        #     "type": "generic",
        #     "motion_type": "smooth",  # Enable smooth motion for demo
        #     "port": 5555,
        #     "asset_path": NVIDIA_ASSETS_ROOT_PATH + "/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd",
        #     "position": [2.0, 0.0, 0.0],  # [x, y, z] in world frame
        #     "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        # },
        {
            "name": "pf400_1",
            "type": "pf400",
            "motion_type": "smooth",  # Enable smooth motion for demo
            "port": 5557,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/pf400.usda",
            "position": [0.0, 0.0, 0.0],  # [x, y, z] in world frame
            "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        },
        {
            "name": "ot2_1",
            "type": "ot2",
            "motion_type": "smooth",  # Enable smooth motion for OT2
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/ot2.usda",
            "position": [0.0, 2.0, 0.0],  # [x, y, z] in world frame
            "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        },
    ]

    # Create robots and their ZMQ servers
    robots, zmq_servers = create_robots(world, robots_config)

    # Reset world to initialize physics
    world.reset()

    # Start all ZMQ servers
    for server in zmq_servers:
        server.start_server()

    # Run simulation loop
    try:
        while simulation_app.is_running():
            # Call robot server update methods each frame
            for server in zmq_servers:
                if hasattr(server, 'update'):
                    server.update()

            # Step the simulation
            world.step(render=True)
    except KeyboardInterrupt:
        pass

    simulation_app.close()

if __name__ == "__main__":
    main()
