from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import json
import sys
import threading

import numpy as np
import zmq

import utils
from isaacsim.core.api import World
from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.rotations import quat_to_euler_angles
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path

ASSETS_ROOT_PATH = get_assets_root_path()
if ASSETS_ROOT_PATH is None:
    print("Error: Could not find Isaac Sim assets folder")
    simulation_app.close()
    sys.exit()


class ZMQRobotServer:
    """Handles ZMQ communication for a single robot"""
    def __init__(self, robot, robot_name: str, port: int):
        self.robot = robot  # Isaac Sim Robot object from world.scene.add(Robot(...))
        self.robot_name = robot_name
        self.port = port
        self.context = None
        self.socket = None

    def start_server(self):
        """Start ZMQ server in background thread"""
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()
        return zmq_thread

    def zmq_server_thread(self):
        """ZMQ server running in background thread"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")

        while simulation_app.is_running():
            try:
                # Receive request with timeout
                if self.socket.poll(100):  # 100ms timeout
                    message = self.socket.recv_string(zmq.NOBLOCK)
                    request = json.loads(message)

                    # Handle command
                    response = self.handle_command(request)

                    # Send response
                    self.socket.send_string(json.dumps(response))

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ZMQ server error for {self.robot_name}: {e}")
                error_response = {"status": "error", "message": str(e)}
                self.socket.send_string(json.dumps(error_response))

        self.socket.close()
        self.context.term()

    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci"""
        action = request.get("action", "")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])
            print(f"Received command for {self.robot_name}: Move robot to joint angles: {joint_angles}")

            if len(joint_angles) != 6:
                return {"status": "error", "message": f"Expected 6 joint angles, got {len(joint_angles)}"}

            try:
                self.robot.set_joint_positions(np.array(joint_angles))
                return {"status": "success", "message": "moved", "joint_angles": joint_angles}
            except Exception as e:
                return {"status": "error", "message": f"Failed to move robot: {str(e)}"}

        elif action == "get_joints":
            print(f"Received command for {self.robot_name}: Get robot joint angles")

            try:
                joint_positions = self.robot.get_joint_positions()
                return {"status": "success", "joint_angles": joint_positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

        elif action == "get_pose":
            print(f"Received command for {self.robot_name}: Get robot end effector pose")

            try:
                joint_positions = self.robot.get_joint_positions()

                # Calculate forward kinematics using utils
                ee_pos, ee_orient = utils.get_robot_end_effector_pose(self.robot)
                # Convert quaternion (w,x,y,z) to euler angles using Isaac Sim utilities
                euler = quat_to_euler_angles(ee_orient)
                pose = [ee_pos[0], ee_pos[1], ee_pos[2], euler[0], euler[1], euler[2]]
                print(f"FK calculated pose: position={ee_pos}, orientation={ee_orient}")

                return {"status": "success", "pose": pose, "joint_angles": joint_positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get pose: {str(e)}"}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}


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

        # Create ZMQ server for this robot
        zmq_server = ZMQRobotServer(robot, config["name"], config["port"])

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
            "port": 5555,
            "asset_path": ASSETS_ROOT_PATH + "/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd",
            "position": [2.0, 0.0, 0.0],  # [x, y, z] in world frame
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
