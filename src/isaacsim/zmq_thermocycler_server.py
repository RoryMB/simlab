from pathlib import Path

import numpy as np
from isaacsim.core.utils.stage import get_current_stage
from isaacsim.core.utils.types import ArticulationAction
from pxr import Gf
from zmq_robot_server import ZMQ_Robot_Server

import utils


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())

class ZMQ_Thermocycler_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for Thermocycler device"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, port)

        # Thermocycler lid joint configuration
        self.lid_open_position = -0.2
        self.lid_closed_position = 0.0

        # Thermocycler raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, 1)  # Upward
        self.raycast_distance = 0.03  # 3cm reach

    def handle_command(self, request):
        """Handle incoming ZMQ command"""
        action = request.get("action", "")

        if action == "open":
            self.current_action = "open_lid"
            self.target_joints = np.array([self.lid_open_position])
            return self.create_success_response("open lid queued")

        elif action == "close":
            self.current_action = "close_lid"
            self.target_joints = np.array([self.lid_closed_position])
            return self.create_success_response("close lid queued")

        elif action == "run_program":
            program_number = request.get("program_number")
            return self.execute_run_program(program_number)

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def execute_run_program(self, program_number):
        """Execute run_program operation - check for plate presence"""
        # Get raycast info
        world_position, world_direction = self._get_end_effector_raycast_info('pointer')

        # Perform raycast to detect plate
        hit_prim = self.raycast(world_position, world_direction, self.raycast_distance, self.robot_prim_path)

        if hit_prim:
            print(f"Robot {self.robot_name} run_program operation (plate detected, program_number={program_number})")
            return self.create_success_response("run_program operation completed", plate_detected=True, program_number=program_number)
        else:
            print(f"Robot {self.robot_name} run_program operation failed (no plate detected)")
            return self.create_error_response("No plate detected in thermocycler")

    def _get_end_effector_raycast_info(self, end_effector_name: str):
        """Transform end effector prim into world position and raycast direction"""
        stage = get_current_stage()
        end_effector_prim_path = f"{self.robot_prim_path}/{end_effector_name}"
        end_effector_prim = stage.GetPrimAtPath(end_effector_prim_path)

        if not end_effector_prim or not end_effector_prim.IsValid():
            raise RuntimeError(f"End effector prim not found at path: {end_effector_prim_path}")

        # Get end effector position and orientation
        end_effector_pos, end_effector_rot = utils.get_xform_world_pose(end_effector_prim)
        quat = Gf.Quatd(float(end_effector_rot[0]), float(end_effector_rot[1]),
                        float(end_effector_rot[2]), float(end_effector_rot[3]))
        rotation = Gf.Rotation(quat)

        # Transform raycast direction from local to world space
        world_direction = rotation.TransformDir(self.raycast_direction)
        world_position = Gf.Vec3d(float(end_effector_pos[0]), float(end_effector_pos[1]),
                                 float(end_effector_pos[2]))

        return world_position, world_direction

    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.is_paused:
            return

        if self.current_action is None:
            return

        if self.current_action in ["open_lid", "close_lid"]:
            self.execute_move_joints()
