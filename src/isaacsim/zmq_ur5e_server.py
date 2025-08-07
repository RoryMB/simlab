import json
import numpy as np
import threading
import zmq

from isaacsim.core.utils.rotations import quat_to_euler_angles

import utils

class ZMQ_UR5e_Server:
    """Handles ZMQ communication for a single robot"""
    def __init__(self, simulation_app, robot, robot_name: str, port: int):
        self.simulation_app = simulation_app
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

        while self.simulation_app.is_running():
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
