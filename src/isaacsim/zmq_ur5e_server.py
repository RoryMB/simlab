import numpy as np
from isaacsim.core.utils.rotations import quat_to_euler_angles
from isaacsim.core.utils.types import ArticulationAction

import utils
from zmq_robot_server import ZMQ_Robot_Server


class ZMQ_UR5e_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for UR5e robot"""
    def __init__(self, simulation_app, robot, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_name, port)

    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci"""
        action = request.get("action", "")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])

            if len(joint_angles) != 6:
                return self.create_error_response(f"Expected 6 joint angles, got {len(joint_angles)}")

            try:
                if self.motion_type == "teleport":
                    self.robot.set_joint_positions(np.array(joint_angles))
                    return self.create_success_response("moved", joint_angles=joint_angles)
                else:  # smooth motion
                    action = ArticulationAction(joint_positions=np.array(joint_angles))
                    self.robot.apply_action(action)
                    return self.create_success_response("started_moving", joint_angles=joint_angles)
            except Exception as e:
                return self.create_error_response(f"Failed to move robot: {str(e)}")

        elif action == "get_joints":
            try:
                joint_positions = self.robot.get_joint_positions()
                return self.create_success_response("joints retrieved", joint_angles=joint_positions.tolist())
            except Exception as e:
                return self.create_error_response(f"Failed to get joint positions: {str(e)}")

        elif action == "get_pose":
            try:
                joint_positions = self.robot.get_joint_positions()

                # Calculate forward kinematics using utils
                ee_pos, ee_orient = utils.get_robot_end_effector_pose(self.robot)
                # Convert quaternion (w,x,y,z) to euler angles using Isaac Sim utilities
                euler = quat_to_euler_angles(ee_orient)
                pose = [ee_pos[0], ee_pos[1], ee_pos[2], euler[0], euler[1], euler[2]]

                return self.create_success_response("pose retrieved", pose=pose, joint_angles=joint_positions.tolist())
            except Exception as e:
                return self.create_error_response(f"Failed to get pose: {str(e)}")

        else:
            return self.create_error_response(f"Unknown action: {action}")
