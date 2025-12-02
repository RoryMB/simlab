from pathlib import Path

import numpy as np
from zmq_robot_server import ZMQ_Robot_Server


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())

class ZMQ_Todo_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot with integrated control"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, port)

    def handle_command(self, request):
        """Handle incoming ZMQ command"""
        action = request.get("action", "")

        if action == "move_joints":
            # return self.create_error_response(f"Expected {expected_joints} joint positions, got {len(joint_positions)}")
            return self.create_success_response("command queued")

        elif action == "get_joints":
            return self.create_success_response("joints retrieved", data={"joint_positions": []})

        elif action == "seal":
            return self.create_success_response("sealed")

        elif action == "peel":
            return self.create_success_response("peeled")

        elif action == "run_program":
            return self.create_success_response("ran program")

        elif action == "run_assay":
            return self.create_success_response("ran assay")

        elif action == "get_status":
            return self.create_success_response("status retrieved", data={"robot_name": self.robot_name})


        elif action == "goto_pose":
            position = request.get("position", [])
            orientation = request.get("orientation", [])

            if len(position) != 3 or len(orientation) != 4:
                return self.create_error_response("goto_pose requires position [x,y,z] and orientation [w,x,y,z]")

            self.current_action = "goto_pose"
            self.target_pose = (np.array(position), np.array(orientation))
            return self.create_success_response("goto_pose queued", position=position, orientation=orientation)

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def update(self):
        """Called every simulation frame to execute robot actions"""
        return
