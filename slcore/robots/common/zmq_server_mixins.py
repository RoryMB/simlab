"""Mixin classes for ZMQ robot servers."""

import math

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

    def _get_plate_relative_yaw(self, plate_prim) -> float:
        """Get the yaw (Z-rotation) of a plate relative to this instrument.

        Computes the relative rotation around the Z axis between the plate
        and the instrument's root prim. This isolates the plate's orientation
        from the instrument's own world rotation.

        Args:
            plate_prim: USD prim of the detected plate

        Returns:
            Relative yaw angle in degrees, normalized to [0, 360).
        """
        stage = get_current_stage()
        robot_prim = stage.GetPrimAtPath(self.robot_prim_path)

        _, plate_rot = utils.get_xform_world_pose(plate_prim)
        _, robot_rot = utils.get_xform_world_pose(robot_prim)

        # Build quaternions (w, x, y, z)
        plate_quat = Gf.Quatd(float(plate_rot[0]), float(plate_rot[1]), float(plate_rot[2]), float(plate_rot[3]))
        robot_quat = Gf.Quatd(float(robot_rot[0]), float(robot_rot[1]), float(robot_rot[2]), float(robot_rot[3]))

        # Relative rotation: robot_inverse * plate
        relative_quat = robot_quat.GetInverse() * plate_quat
        relative_rotation = Gf.Rotation(relative_quat)

        # Decompose to axis/angle -- project onto Z axis for yaw
        axis = relative_rotation.GetAxis()
        angle = relative_rotation.GetAngle()

        # The yaw is the component of rotation around Z
        # For a rotation primarily around Z, axis.GetZ() will be close to +/-1
        yaw = angle * axis[2]

        # Normalize to [0, 360)
        yaw = yaw % 360
        return yaw

    def _check_plate_orientation(self, plate_prim, expected_yaw: float, tolerance: float = 15.0) -> tuple[bool, float]:
        """Check if a plate's relative yaw matches the expected orientation.

        Accounts for 180-degree equivalence (0 == 180, 90 == 270) since
        microplates are symmetric about both axes.

        Args:
            plate_prim: USD prim of the detected plate
            expected_yaw: Expected relative yaw in degrees (0, 90, 180, or 270)
            tolerance: Acceptable deviation in degrees (default: 15)

        Returns:
            Tuple of (orientation_ok, actual_yaw)
        """
        actual_yaw = self._get_plate_relative_yaw(plate_prim)

        # Check against expected and its 180-degree equivalent
        equivalent_yaw = (expected_yaw + 180) % 360
        for target in [expected_yaw, equivalent_yaw]:
            diff = abs(actual_yaw - target)
            # Handle wraparound (e.g., 359 vs 0)
            diff = min(diff, 360 - diff)
            if diff <= tolerance:
                return True, actual_yaw

        return False, actual_yaw
