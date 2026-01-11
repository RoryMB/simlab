from pathlib import Path
import numpy as np

from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
from isaacsim.storage.native import get_assets_root_path
from omni.physx import get_physx_simulation_interface
from omni.physx.bindings._physx import ContactEventType
from omni.physx.scripts.physicsUtils import PhysicsSchemaTools
from pxr import PhysxSchema, UsdPhysics

from slcore.common import utils
from slcore.robots.common.config import ASSETS_ROOT, PhysicsConfig, DEFAULT_PHYSICS_CONFIG
from slcore.robots.common.validation import validate_prim_exists
from slcore.robots.ot2.zmq_ot2_server import ZMQ_OT2_Server
from slcore.robots.ur5e.zmq_ur5e_server import ZMQ_UR5e_Server
from slcore.robots.pf400.zmq_pf400_server import ZMQ_PF400_Server
from slcore.robots.sealer.zmq_sealer_server import ZMQ_Sealer_Server
from slcore.robots.peeler.zmq_peeler_server import ZMQ_Peeler_Server
from slcore.robots.thermocycler.zmq_thermocycler_server import ZMQ_Thermocycler_Server
from slcore.robots.hidex.zmq_hidex_server import ZMQ_Hidex_Server


CUSTOM_ASSETS_ROOT_PATH = str(ASSETS_ROOT)
NVIDIA_ASSETS_ROOT_PATH = get_assets_root_path()

# Robot server registry for factory pattern
ROBOT_SERVER_REGISTRY = {
    "ot2": ZMQ_OT2_Server,
    "pf400": ZMQ_PF400_Server,
    "ur5e": ZMQ_UR5e_Server,
    "sealer": ZMQ_Sealer_Server,
    "peeler": ZMQ_Peeler_Server,
    "thermocycler": ZMQ_Thermocycler_Server,
    "hidex": ZMQ_Hidex_Server,
}


def create_zmq_server(robot_type: str, simulation_app, robot, robot_prim_path: str, robot_name: str, port: int):
    """Factory function to create ZMQ server for a given robot type.

    Args:
        robot_type: Type of robot (e.g., "ur5e", "pf400", "ot2")
        simulation_app: Isaac Sim application instance
        robot: Robot object
        robot_prim_path: USD prim path for the robot
        robot_name: Name identifier for the robot
        port: ZMQ port number

    Returns:
        ZMQ server instance for the robot type

    Raises:
        ValueError: If robot type is not recognized
    """
    server_class = ROBOT_SERVER_REGISTRY.get(robot_type)
    if server_class is None:
        raise ValueError(f"Unknown robot type: {robot_type}. Available types: {list(ROBOT_SERVER_REGISTRY.keys())}")
    return server_class(simulation_app, robot, robot_prim_path, robot_name, port)


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

    robot_prim = validate_prim_exists(world.stage, robot_config['prim_path'])

    if "position" in robot_config:
        position = np.array(robot_config["position"])
        orientation = np.array(robot_config.get("orientation", [1.0, 0.0, 0.0, 0.0]))

        utils.set_xform_world_pose(robot_prim, position, orientation)

    robot = world.scene.add(Robot(
        prim_path=robot_config['prim_path'],
        name=robot_config["name"],
    ))

    # Create appropriate ZMQ server based on robot type using factory pattern
    robot_type = robot_config["type"]
    zmq_server = create_zmq_server(
        robot_type,
        simulation_app,
        robot,
        robot_config["prim_path"],
        robot_config["name"],
        robot_config["port"]
    )

    # Enable collision detection
    contact_report_api = PhysxSchema.PhysxContactReportAPI.Apply(robot_prim)
    contact_report_api.CreateThresholdAttr().Set(0.0)

    # Set contact offset for robot for precise collision detection
    # This needs to be applied to all collision shapes in the robot hierarchy
    stage = get_current_stage()
    for prim in stage.Traverse():
        prim_path = str(prim.GetPath())
        if prim_path.startswith(robot_prim.GetPath().pathString):
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                physx_collision = PhysxSchema.PhysxCollisionAPI.Apply(prim)
                physx_collision.CreateContactOffsetAttr().Set(DEFAULT_PHYSICS_CONFIG.contact_offset)

    return robot, zmq_server
