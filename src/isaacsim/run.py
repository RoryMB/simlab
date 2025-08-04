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

class IsaacSimStuff:
    def __init__(self, port=5555):
        self.port = port
        self.robot = None
        self.world = None
        self.running = False

    def setup_scene(self):
        """Setup a scene in Isaac Sim with a UR5e robot."""
        # Create world
        self.world = World(stage_units_in_meters=1.0)
        self.world.scene.add_default_ground_plane()

        # Get assets and add robot
        assets_root_path = get_assets_root_path()
        if assets_root_path is None:
            print("Error: Could not find Isaac Sim assets folder")
            simulation_app.close()
            sys.exit()
            return False

        ur5e_asset_path = assets_root_path + "/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd"
        add_reference_to_stage(usd_path=ur5e_asset_path, prim_path="/World/UR5e")

        self.robot = self.world.scene.add(Robot(prim_path="/World/UR5e", name="ur5e_robot"))

        # Reset world to initialize physics
        self.world.reset()

        return True

    def zmq_server_thread(self):
        """ZMQ server running in background thread."""
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://*:{self.port}")

        while self.running:
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

            # Enhanced validation
            if len(joint_angles) != 6:
                return {"status": "error", "message": f"Expected 6 joint angles, got {len(joint_angles)}"}

            # Validate joint angle ranges (UR5e limits)
            joint_limits = [
                (-2*np.pi, 2*np.pi),  # Base
                (-2*np.pi, 2*np.pi),  # Shoulder
                (-np.pi, np.pi),      # Elbow
                (-2*np.pi, 2*np.pi),  # Wrist 1
                (-2*np.pi, 2*np.pi),  # Wrist 2
                (-2*np.pi, 2*np.pi)   # Wrist 3
            ]

            for i, (angle, (min_val, max_val)) in enumerate(zip(joint_angles, joint_limits)):
                if not (min_val <= angle <= max_val):
                    return {
                        "status": "error",
                        "message": f"Joint {i+1} angle {angle:.3f} out of range [{min_val:.3f}, {max_val:.3f}]",
                    }

            try:
                print(f"Received command: Moving robot to joint angles: {joint_angles}")
                self.robot.set_joint_positions(np.array(joint_angles))
                return {"status": "success", "message": "moved", "joint_angles": joint_angles}
            except Exception as e:
                return {"status": "error", "message": f"Failed to move robot: {str(e)}"}

        elif action == "get_joints":
            try:
                positions = self.robot.get_joint_positions()
                return {"status": "success", "joint_angles": positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

        elif action == "get_pose":
            try:
                # Get end-effector pose (simplified)
                joint_positions = self.robot.get_joint_positions()
                # For a real implementation, you'd calculate forward kinematics here
                # For now, return a placeholder pose
                pose = [0.5, 0.0, 1.0, 0.0, 0.0, 0.0]  # [x,y,z,rx,ry,rz]
                return {"status": "success", "pose": pose, "joint_angles": joint_positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get pose: {str(e)}"}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def run(self):
        """Run the complete Isaac Sim loop."""
        if not self.setup_scene():
            return

        # Start ZMQ server in background thread
        self.running = True
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()

        # Run Isaac Sim simulation loop
        try:
            while simulation_app.is_running():
                self.world.step(render=True)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

if __name__ == "__main__":
    server = IsaacSimStuff()
    server.run()

    simulation_app.close()
