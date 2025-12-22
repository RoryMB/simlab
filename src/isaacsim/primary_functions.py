from pathlib import Path
import numpy as np

from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
from isaacsim.storage.native import get_assets_root_path
from omni.physx import get_physx_simulation_interface
from omni.physx.bindings._physx import ContactEventType
from omni.physx.scripts.physicsUtils import PhysicsSchemaTools
from pxr import PhysxSchema, UsdPhysics

import utils
from zmq_ot2_server import ZMQ_OT2_Server
from zmq_ur5e_server import ZMQ_UR5e_Server
from zmq_pf400_server import ZMQ_PF400_Server
from zmq_todo_server import ZMQ_Todo_Server
from zmq_sealer_server import ZMQ_Sealer_Server
from zmq_peeler_server import ZMQ_Peeler_Server
from zmq_thermocycler_server import ZMQ_Thermocycler_Server
from zmq_hidex_server import ZMQ_Hidex_Server


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
        self._contact_report_sub = get_physx_simulation_interface().subscribe_contact_report_events(
            self.on_collision
        )

    def on_collision(self, contact_headers, contact_data):
        """Handle collision events and notify all robot servers"""

        for contact_header in contact_headers:
            if contact_header.type != ContactEventType.CONTACT_FOUND:
                continue

            actor0 = str(PhysicsSchemaTools.intToSdfPath(contact_header.actor0))
            actor1 = str(PhysicsSchemaTools.intToSdfPath(contact_header.actor1))

            print(f"Collision detected: {actor0} <-> {actor1}")

            # Notify all robot servers - they decide what to care about
            for robot_name, server in self.robot_servers.items():
                if hasattr(server, 'on_collision'):
                    server.on_collision(actor0, actor1)


def create_robot(simulation_app, world, robot_config, add=True):
    """Create robots and their ZMQ servers"""
    # Create robot in simulation
    if add:
        add_reference_to_stage(
            usd_path=robot_config["asset_path"],
            prim_path=robot_config['prim_path'],
        )

    robot_prim = world.stage.GetPrimAtPath(robot_config['prim_path'])

    if "position" in robot_config:
        position = np.array(robot_config["position"])
        orientation = np.array(robot_config.get("orientation", [1.0, 0.0, 0.0, 0.0]))

        utils.set_prim_world_pose(robot_prim, position=position, orientation=orientation)

    robot = world.scene.add(Robot(
        prim_path=robot_config['prim_path'],
        name=robot_config["name"],
    ))

    # Create appropriate ZMQ server based on robot type
    robot_type = robot_config["type"]

    if robot_type == "ot2":
        zmq_server = ZMQ_OT2_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "pf400":
        zmq_server = ZMQ_PF400_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "ur5e":
        zmq_server = ZMQ_UR5e_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "todo":
        zmq_server = ZMQ_Todo_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "sealer":
        zmq_server = ZMQ_Sealer_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "peeler":
        zmq_server = ZMQ_Peeler_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "thermocycler":
        zmq_server = ZMQ_Thermocycler_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    elif robot_type == "hidex":
        zmq_server = ZMQ_Hidex_Server(simulation_app, robot, robot_config["prim_path"], robot_config["name"], robot_config["port"])
    else:
        raise RuntimeError(f"Robot type {robot_type} not recognized")

    # Enable collision detection
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(robot_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)

    # Set contact offset for robot to 0 for precise collision detection
    # This needs to be applied to all collision shapes in the robot hierarchy
    stage = get_current_stage()
    for prim in stage.Traverse():
        prim_path = str(prim.GetPath())
        if prim_path.startswith(robot_prim.GetPath().pathString):
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                physx_collision = PhysxSchema.PhysxCollisionAPI.Apply(prim)
                physx_collision.CreateContactOffsetAttr().Set(0.0001)

    return robot, zmq_server
