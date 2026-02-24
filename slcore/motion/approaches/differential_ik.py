"""Differential IK motion approach.

Wraps the existing DifferentialIKSolver to provide the MotionApproach
interface. This approach only provides IK capability (no trajectory
generation or collision awareness).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from slcore.motion.base import IKError, MotionApproach, MotionResult
from slcore.motion.capabilities import MotionCapability

if TYPE_CHECKING:
    from slcore.robots.common.config import DifferentialIKConfig
    from slcore.robots.common.differential_ik_solver import DifferentialIKSolver
    from slcore.robots.common.isaaclab_articulation import ArticulationViewWrapper


class DifferentialIKApproach(MotionApproach):
    """Motion approach using Isaac Lab's differential IK controller.

    This approach provides only IK capability. It computes joint positions
    to achieve a target end-effector pose using iterative differential IK.

    Attributes:
        solver: The underlying DifferentialIKSolver instance
    """

    def __init__(
        self,
        articulation: ArticulationViewWrapper,
        config: DifferentialIKConfig,
        joint_names: list[str],
        device: str = "cuda:0",
    ):
        """Initialize the differential IK approach.

        Args:
            articulation: Isaac Lab Articulation instance
            config: Differential IK configuration from YAML
            joint_names: List of joint names to control
            device: Torch device for computations
        """
        # Deferred import to avoid Isaac Sim dependency at module load time
        from slcore.robots.common.differential_ik_solver import DifferentialIKSolver

        self.solver = DifferentialIKSolver(
            articulation=articulation,
            config=config,
            joint_names=joint_names,
            device=device,
        )
        self.config = config

    def capabilities(self) -> MotionCapability:
        """Return capabilities: IK only.

        Returns:
            MotionCapability.IK
        """
        return MotionCapability.IK

    def compute_motion(
        self,
        target_position: np.ndarray,
        target_orientation: np.ndarray,
        solution_preference: str = "closest_to_current",
        **kwargs,
    ) -> MotionResult:
        """Compute joint positions to achieve target pose.

        Args:
            target_position: Target position [x, y, z] in world frame (meters)
            target_orientation: Target orientation quaternion [w, x, y, z]
            solution_preference: IK solution preference:
                - "closest_to_current": Minimize movement from current joints
                - "closest_to_home": Prefer configurations near home pose
            **kwargs: Ignored (for interface compatibility)

        Returns:
            MotionResult with computed joint positions

        Raises:
            IKError: If IK fails to find a solution
        """
        joint_positions, success = self.solver.compute_inverse_kinematics(
            target_position=target_position,
            target_orientation=target_orientation,
            solution_preference=solution_preference,
        )

        if not success:
            raise IKError(
                target_position=target_position,
                target_orientation=target_orientation,
                message=(
                    f"Differential IK failed for position={target_position.tolist()}, "
                    f"orientation={target_orientation.tolist()}"
                ),
            )

        return MotionResult(
            success=True,
            joint_positions=joint_positions,
        )

    def reset(self):
        """Reset the controller state."""
        self.solver.reset()

    def set_robot_base_pose(self, position: np.ndarray, orientation: np.ndarray):
        """Update the robot base pose for IK calculations.

        This must be called before compute_motion() if the robot base
        has moved since initialization.

        Args:
            position: Base position [x, y, z] in world frame
            orientation: Base orientation quaternion [w, x, y, z]
        """
        self.solver.set_robot_base_pose(position, orientation)
