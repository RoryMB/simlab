from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import numpy as np
import sys
import json
import threading
import zmq
from isaacsim.core.api import World
from isaacsim.core.api.robots import Robot
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
                # TODO: Calculate forward kinematics
                # For now, return a placeholder pose
                pose = [0.5, 0.0, 1.0, 0.0, 0.0, 0.0]  # [x,y,z,rx,ry,rz]
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
