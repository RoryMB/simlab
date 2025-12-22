from pathlib import Path

import numpy as np
from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf
from zmq_robot_server import ZMQ_Robot_Server

import utils


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())

class ZMQ_Sealer_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for Sealer device"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, port)

        # Sealer raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, 1)  # Upward
        self.raycast_distance = 0.03  # 3cm reach

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
        """Called every simulation frame - no continuous actions needed for sealer"""
        pass
