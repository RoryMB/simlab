"""Mixin classes for ZMQ robot servers."""

from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf

from slcore.common import utils


class RaycastMixin:
    """Mixin for robots that need raycast-based object detection.

    Provides end effector raycast functionality for gripping operations.
    Requires the class to have:
        - robot_prim_path: str
        - raycast_direction: Gf.Vec3d
    """

    def _get_end_effector_raycast_info(self, end_effector_name: str):
        """Transform end effector prim into world position and raycast direction.

        Args:
            end_effector_name: Name of the end effector prim (e.g., 'pointer')

        Returns:
            Tuple of (world_position: Gf.Vec3d, world_direction: Gf.Vec3d)

        Raises:
            RuntimeError: If end effector prim is not found
        """
        stage = get_current_stage()
        end_effector_prim_path = f"{self.robot_prim_path}/{end_effector_name}"
        end_effector_prim = stage.GetPrimAtPath(end_effector_prim_path)

        if not end_effector_prim or not end_effector_prim.IsValid():
            raise RuntimeError(f"End effector prim not found at path: {end_effector_prim_path}")

        # Get end effector position and orientation
        end_effector_pos, end_effector_rot = utils.get_xform_world_pose(end_effector_prim)
        quat = Gf.Quatd(
            float(end_effector_rot[0]),
            float(end_effector_rot[1]),
            float(end_effector_rot[2]),
            float(end_effector_rot[3])
        )
        rotation = Gf.Rotation(quat)

        # Transform raycast direction from local to world space
        world_direction = rotation.TransformDir(self.raycast_direction)
        world_position = Gf.Vec3d(
            float(end_effector_pos[0]),
            float(end_effector_pos[1]),
            float(end_effector_pos[2])
        )

        return world_position, world_direction
