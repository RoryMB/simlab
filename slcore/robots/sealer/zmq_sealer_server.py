from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf

from slcore.common import utils
from slcore.robots.common.zmq_robot_server import ZMQ_Robot_Server
from slcore.robots.common.config import DEFAULT_PHYSICS_CONFIG
from slcore.robots.common.zmq_server_mixins import RaycastMixin


class ZMQ_Sealer_Server(RaycastMixin, ZMQ_Robot_Server):
    """Handles ZMQ communication for Sealer device"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, port)

        # Sealer raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, 1)  # Upward
        self.raycast_distance = DEFAULT_PHYSICS_CONFIG.raycast_distance

    def handle_command(self, request):
        """Handle incoming ZMQ command"""
        action = request.get("action", "")

        if action == "seal":
            return self.execute_seal()
        else:
            return self.create_error_response(f"Unknown action: {action}")

    def execute_seal(self):
        """Execute seal operation - check for plate presence"""
        # Get raycast info
        world_position, world_direction = self._get_end_effector_raycast_info('pointer')

        # Perform raycast to detect plate
        hit_prim = self.raycast(world_position, world_direction, self.raycast_distance, self.robot_prim_path)

        if hit_prim:
            print(f"Robot {self.robot_name} seal operation (plate detected)")
            return self.create_success_response("seal operation completed", plate_detected=True)
        else:
            print(f"Robot {self.robot_name} seal operation failed (no plate detected)")
            return self.create_error_response("No plate detected at sealer location")

    # _get_end_effector_raycast_info is inherited from RaycastMixin

    def update(self):
        """Called every simulation frame - no continuous actions needed for sealer"""
        pass
