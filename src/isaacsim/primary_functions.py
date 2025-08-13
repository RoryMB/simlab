from pathlib import Path
import numpy as np

from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path
from omni.physx.bindings._physx import ContactEventType
from omni.physx.scripts.physicsUtils import PhysicsSchemaTools

import utils
from zmq_ot2_server import ZMQ_OT2_Server
from zmq_ur5e_server import ZMQ_UR5e_Server
from zmq_pf400_server import ZMQ_PF400_Server


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())
NVIDIA_ASSETS_ROOT_PATH = get_assets_root_path()
# if NVIDIA_ASSETS_ROOT_PATH is None:
#     print("Error: Could not find Isaac Sim assets folder")
#     simulation_app.close()
#     sys.exit()


class CollisionDetector:
    """Handles collision detection and notifies robot servers"""

    def __init__(self, robot_servers):
        self.robot_servers = robot_servers  # Dict of {robot_name: server}

    def on_collision(self, contact_headers, contact_data):
        """Handle collision events and notify affected robot servers"""

        for contact_header in contact_headers:
            if contact_header.type != ContactEventType.CONTACT_FOUND:
                continue

            actor0 = str(PhysicsSchemaTools.intToSdfPath(contact_header.actor0))
            actor1 = str(PhysicsSchemaTools.intToSdfPath(contact_header.actor1))

            print(f"Collision detected: {actor0} <-> {actor1}")

            # Check which robot servers are affected by this collision
            for robot_name, server in self.robot_servers.items():
                robot_prim_path = f"/World/{robot_name}"

                if actor0.startswith(robot_prim_path) or actor1.startswith(robot_prim_path):
                    print(f"Notifying {robot_name} server of collision")
                    if hasattr(server, 'on_collision'):
                        server.on_collision(actor0, actor1)


def create_robot(simulation_app, world, robot_config):
    """Create robots and their ZMQ servers"""
    # Create robot in simulation
    add_reference_to_stage(
        usd_path=robot_config["asset_path"],
        prim_path=f"/World/{robot_config['name']}",
    )
    if "position" in robot_config:
        robot_prim = world.stage.GetPrimAtPath(f"/World/{robot_config['name']}")

        position = np.array(robot_config["position"])
        orientation = np.array(robot_config.get("orientation", [1.0, 0.0, 0.0, 0.0]))

        utils.set_prim_world_pose(robot_prim, position=position, orientation=orientation)

    robot = world.scene.add(Robot(
        prim_path=f"/World/{robot_config['name']}",
        name=robot_config["name"],
    ))

    # Create appropriate ZMQ server based on robot type
    robot_type = robot_config["type"]

    if robot_type == "ot2":
        zmq_server = ZMQ_OT2_Server(simulation_app, robot, robot_config["name"], robot_config["port"])
    elif robot_type == "pf400":
        zmq_server = ZMQ_PF400_Server(simulation_app, robot, robot_config["name"], robot_config["port"])
    elif robot_type == "ur5e":
        zmq_server = ZMQ_UR5e_Server(simulation_app, robot, robot_config["name"], robot_config["port"])
    else:
        raise RuntimeError(f"Robot type {robot_type} not recognized")

    return robot, zmq_server
