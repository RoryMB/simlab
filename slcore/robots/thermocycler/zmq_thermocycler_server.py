import numpy as np
from isaacsim.core.utils.types import ArticulationAction
from pxr import Gf

from slcore.robots.common.zmq_robot_server import ZMQ_Robot_Server
from slcore.robots.common.zmq_server_mixins import RaycastMixin

class ZMQ_Thermocycler_Server(RaycastMixin, ZMQ_Robot_Server):
    """Handles ZMQ communication for Thermocycler device"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, env_id: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, env_id)

        # Thermocycler lid joint configuration
        self.lid_open_position = -0.2
        self.lid_closed_position = 0.0

        # Thermocycler raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, 1)  # Upward
        self.raycast_distance = 0.03  # 3cm reach

    def handle_command(self, request: dict) -> dict:
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

    # _get_end_effector_raycast_info is inherited from RaycastMixin

    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.is_paused:
            return

        if self.current_action is None:
            return

        if self.current_action in ["open_lid", "close_lid"]:
            self.execute_move_joints()
