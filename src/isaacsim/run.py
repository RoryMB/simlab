from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import sys
from pathlib import Path
import numpy as np

from isaacsim.core.api import World
from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path

import utils
from zmq_ot2_server import ZMQ_OT2_Server
from zmq_ur5e_server import ZMQ_UR5e_Server

CUSTOM_ASSETS_ROOT_PATH = str(Path("../../assets").resolve())

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
        if robot_type == "ot2":
            zmq_server = ZMQ_OT2_Server(simulation_app, robot, config["name"], config["port"])
        else:
            # Default to generic robot server (for UR5e, etc.)
            zmq_server = ZMQ_UR5e_Server(simulation_app, robot, config["name"], config["port"])

        robots.append(robot)
        zmq_servers.append(zmq_server)

    return robots, zmq_servers


def main():
    # Create world
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    # Robot configuration
    robots_config = [
        {
            "name": "ur5e_robot",
            "type": "generic",
            "port": 5555,
            "asset_path": NVIDIA_ASSETS_ROOT_PATH + "/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd",
            "position": [2.0, 0.0, 0.0],  # [x, y, z] in world frame
            "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        },
        {
            "name": "ot2_robot",
            "type": "ot2",
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/ot2.usda",
            "position": [0.0, 2.0, 0.0],  # [x, y, z] in world frame
            "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        }
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
            world.step(render=True)
    except KeyboardInterrupt:
        pass

    simulation_app.close()

if __name__ == "__main__":
    main()
