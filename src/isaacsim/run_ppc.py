"""
run_ppc.py - Pick Place and Collision Detection Demo
Modern Isaac Sim script with hardcoded scene setup inspired by simple_plate_transfer.usda
Integrates robot control into simulation loop for collision detection while maintaining
per-robot ZMQ server architecture
"""

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
from isaacsim.core.utils.prims import create_prim, get_prim_at_path
from omni.physx import get_physx_simulation_interface
from omni.physx.bindings._physx import ContactEventType
from omni.physx.scripts.physicsUtils import PhysicsSchemaTools
from pxr import PhysxSchema

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

    collision_cube_prim = create_prim(
        prim_path="/World/collision_cube",
        prim_type="Cube",
        position=np.array([0.0, -1.8, 0.5]),
        scale=np.array([0.5, 0.5, 0.5]),
    )

    # Add colliders to all cubes using the utility function
    utils.add_collider_to_prim(platform1_prim)
    utils.add_collider_to_prim(platform2_prim)
    utils.add_collider_to_prim(collision_cube_prim)

    # Create reference position markers (invisible prims for navigation)
    high_prim = create_prim(
        prim_path="/World/high",
        prim_type="Xform",
        position=np.array([0.245, 0.0, 1.043]),
    )

    # Side position at (0.3, 0.3, 0.3) - same as microplate for pickup
    side_prim = create_prim(
        prim_path="/World/side",
        prim_type="Xform",
        position=np.array([0.3, 0.3, 0.3]),
    )

    # Coll position at (0.3, -0.3, 0.3) - for collision testing
    coll_prim = create_prim(
        prim_path="/World/coll",
        prim_type="Xform",
        position=np.array([0.3, -0.3, 0.3]),
    )

    return {
        "microplate": microplate_prim,
        "platform1": platform1_prim,
        "platform2": platform2_prim,
        "collision_cube": collision_cube_prim,
        "high": high_prim,
        "side": side_prim,
        "coll": coll_prim,
    }


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


def main():
    # Create world
    world = World(stage_units_in_meters=1.0)

    # Create scene objects
    scene_objects = create_scene_objects(world)

    # Robot configuration
    robots_config = [
        {
            "name": "pf400",
            "type": "pf400",
            "motion_type": "smooth",
            "port": 5557,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/pf400.usda",
            "position": [0.0, 0.0, 0.0],
            "orientation": [1.0, 0.0, 0.0, 0.0],
        }
    ]

    # Create robots and their ZMQ servers
    robots, zmq_servers = create_robots(world, robots_config)

    # Enable collision detection on robot
    pf400_prim = get_prim_at_path("/World/pf400")
    PhysxSchema.PhysxContactReportAPI.Apply(pf400_prim)

    # Setup collision detector
    robot_servers = {"pf400": zmq_servers[0]}  # Using the first (and only) server
    collision_detector = CollisionDetector(robot_servers)

    # Subscribe to collision events
    collision_subscription = get_physx_simulation_interface().subscribe_contact_report_events(collision_detector.on_collision)

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
