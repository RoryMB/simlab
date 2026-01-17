import numpy as np
from pxr import Gf

from slcore.robots.common.zmq_robot_server import ZMQ_Robot_Server
from slcore.robots.common.zmq_server_mixins import RaycastMixin

class ZMQ_Peeler_Server(RaycastMixin, ZMQ_Robot_Server):
    """Handles ZMQ communication for Peeler device"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, env_id: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, env_id)

        # Peeler raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, 1)  # Upward
        self.raycast_distance = 0.03  # 3cm reach

    def handle_command(self, request: dict) -> dict:
        """Handle incoming ZMQ command"""
        action = request.get("action", "")

        if action == "peel":
            return self.execute_peel()
        else:
            return self.create_error_response(f"Unknown action: {action}")

    def execute_peel(self):
        """Execute peel operation - check for plate presence"""
        # Get raycast info
        world_position, world_direction = self._get_end_effector_raycast_info('pointer')

        # Perform raycast to detect plate
        hit_prim = self.raycast(world_position, world_direction, self.raycast_distance, self.robot_prim_path)

        if hit_prim:
            print(f"Robot {self.robot_name} peel operation (plate detected)")
            return self.create_success_response("peel operation completed", plate_detected=True)
        else:
            print(f"Robot {self.robot_name} peel operation failed (no plate detected)")
            return self.create_error_response("No plate detected at peeler location")

    def update(self):
        """Called every simulation frame - no continuous actions needed for peeler"""
        pass
