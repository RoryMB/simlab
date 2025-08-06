from isaacsim import SimulationApp

# Launch Isaac Sim in GUI mode
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

class IsaacSimStuff:
    def __init__(self, port=5555):
        self.port = port
        self.robot = None
        self.world = None

        # Create world
        self.world = World(stage_units_in_meters=1.0)
        self.world.scene.add_default_ground_plane()

        # Add the robot
        ur5e_asset_path = ASSETS_ROOT_PATH + "/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd"
        add_reference_to_stage(usd_path=ur5e_asset_path, prim_path="/World/ur5e")
        self.robot = self.world.scene.add(Robot(prim_path="/World/ur5e", name="ur5e_robot"))

        # Reset world to initialize physics
        self.world.reset()

    def zmq_server_thread(self):
        """ZMQ server running in background thread."""
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://*:{self.port}")

        while simulation_app.is_running():
            try:
                # Receive request with timeout
                if socket.poll(100):  # 100ms timeout
                    message = socket.recv_string(zmq.NOBLOCK)
                    request = json.loads(message)

                    # Handle command
                    response = self.handle_command(request)

                    # Send response
                    socket.send_string(json.dumps(response))

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ZMQ server error: {e}")
                error_response = {"status": "error", "message": str(e)}
                socket.send_string(json.dumps(error_response))

        socket.close()
        context.term()

    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci."""
        action = request.get("action", "")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])
            print(f"Received command: Move robot to joint angles: {joint_angles}")

            if len(joint_angles) != 6:
                return {"status": "error", "message": f"Expected 6 joint angles, got {len(joint_angles)}"}

            try:
                self.robot.set_joint_positions(np.array(joint_angles))
                return {"status": "success", "message": "moved", "joint_angles": joint_angles}
            except Exception as e:
                return {"status": "error", "message": f"Failed to move robot: {str(e)}"}

        elif action == "get_joints":
            print(f"Received command: Get robot joint angles: {joint_angles}")

            try:
                joint_positions = self.robot.get_joint_positions()
                return {"status": "success", "joint_angles": joint_positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

        elif action == "get_pose":
            print(f"Received command: Get robot end effector pose: {joint_angles}")

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

    def run(self):
        """Run the complete Isaac Sim loop."""
        # Start ZMQ server in background thread
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()

        # Run Isaac Sim simulation loop
        try:
            while simulation_app.is_running():
                self.world.step(render=True)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    server = IsaacSimStuff()
    server.run()

    simulation_app.close()
