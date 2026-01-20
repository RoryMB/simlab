"""Differential IK solver using Isaac Lab's DifferentialIKController.

This module wraps Isaac Lab's DifferentialIKController to provide an interface
compatible with the existing ZMQ robot server pattern. It computes joint
positions to achieve target end-effector poses using differential inverse
kinematics.

NOTE: Isaac Lab modules (isaaclab.*) are only available after Isaac Sim
has started and loaded its extensions. All imports are deferred.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch

from slcore.robots.common.config import DifferentialIKConfig

if TYPE_CHECKING:
    from isaaclab.assets import Articulation


class DifferentialIKSolver:
    """Wraps Isaac Lab's DifferentialIKController for use in Simlab.

    This solver computes joint positions to achieve a target end-effector pose
    using differential inverse kinematics. It requires an Isaac Lab Articulation
    to access Jacobian matrices.

    Attributes:
        articulation: Isaac Lab Articulation instance
        config: Differential IK configuration parameters
        controller: Isaac Lab DifferentialIKController instance
    """

    def __init__(
        self,
        articulation: Articulation,
        config: DifferentialIKConfig,
        joint_names: list[str],
        device: str = "cuda:0",
    ):
        """Initialize the differential IK solver.

        Args:
            articulation: Isaac Lab Articulation instance (wrapping existing prim)
            config: Differential IK configuration from YAML
            joint_names: List of joint names to control (must match articulation)
            device: Torch device for computations
        """
        self.articulation = articulation
        self.config = config
        self.device = device

        # Resolve joint and body indices from names
        self._resolve_indices(joint_names)

        # Create the Isaac Lab controller
        self._create_controller()

        # Initialize robot base pose (updated before each IK solve)
        self.robot_base_pos = torch.zeros(1, 3, device=device)
        self.robot_base_quat = torch.tensor([[1.0, 0.0, 0.0, 0.0]], device=device)

    def _resolve_indices(self, joint_names: list[str]):
        """Resolve joint and body indices from names.

        Args:
            joint_names: List of joint names to control

        Raises:
            ValueError: If a joint or body name is not found
        """
        # Get joint indices
        all_joint_names = self.articulation.data.joint_names
        self.joint_ids = []
        for name in joint_names:
            if name in all_joint_names:
                self.joint_ids.append(all_joint_names.index(name))
            else:
                raise ValueError(
                    f"Joint '{name}' not found in articulation. "
                    f"Available joints: {all_joint_names}"
                )

        # Get end effector body index
        all_body_names = self.articulation.data.body_names
        ee_name = self.config.end_effector_body_name
        if ee_name in all_body_names:
            self.ee_body_idx = all_body_names.index(ee_name)
        else:
            raise ValueError(
                f"Body '{ee_name}' not found in articulation. "
                f"Available bodies: {all_body_names}"
            )

        # Jacobian index adjustment for fixed-base robots
        # In the Jacobian, body indices are offset by -1 for fixed-base robots
        self.ee_jacobi_idx = (
            self.ee_body_idx - 1
            if self.articulation.is_fixed_base
            else self.ee_body_idx
        )

    def _create_controller(self):
        """Create the Isaac Lab DifferentialIKController."""
        # Deferred import - only available after Isaac Sim starts
        from isaaclab.controllers import (
            DifferentialIKController,
            DifferentialIKControllerCfg,
        )

        # Build IK parameters dict based on method
        ik_params = None
        if self.config.ik_method == "dls":
            ik_params = {"lambda_val": self.config.lambda_val}

        # Create controller configuration
        controller_cfg = DifferentialIKControllerCfg(
            command_type="pose",
            use_relative_mode=False,
            ik_method=self.config.ik_method,
            ik_params=ik_params,
        )

        # Create controller (num_envs=1 for single robot)
        self.controller = DifferentialIKController(
            controller_cfg,
            num_envs=1,
            device=self.device,
        )

    def set_robot_base_pose(self, position: np.ndarray, orientation: np.ndarray):
        """Update the robot base pose for IK calculations.

        The base pose is used to transform target poses from world frame
        to robot base frame before computing IK.

        Args:
            position: Base position [x, y, z] in world frame
            orientation: Base orientation quaternion [w, x, y, z]
        """
        self.robot_base_pos = torch.tensor(
            position.reshape(1, 3),
            device=self.device,
            dtype=torch.float32,
        )
        self.robot_base_quat = torch.tensor(
            orientation.reshape(1, 4),
            device=self.device,
            dtype=torch.float32,
        )

    def compute_inverse_kinematics(
        self,
        target_position: np.ndarray,
        target_orientation: np.ndarray,
    ) -> tuple[np.ndarray, bool]:
        """Compute joint positions to achieve target end-effector pose.

        Args:
            target_position: Target position [x, y, z] in world frame (meters)
            target_orientation: Target orientation quaternion [w, x, y, z]

        Returns:
            Tuple of (joint_positions, success) where:
                - joint_positions: Computed joint angles (numpy array)
                - success: True if IK found a valid solution
        """
        # Deferred import - only available after Isaac Sim starts
        from isaaclab.utils.math import subtract_frame_transforms

        # Convert inputs to tensors
        target_pos = torch.tensor(
            target_position.reshape(1, 3),
            device=self.device,
            dtype=torch.float32,
        )
        target_quat = torch.tensor(
            target_orientation.reshape(1, 4),
            device=self.device,
            dtype=torch.float32,
        )

        # Set target command (pose = [x, y, z, qw, qx, qy, qz])
        command = torch.cat([target_pos, target_quat], dim=1)
        self.controller.set_command(command)

        # Refresh articulation data buffers
        self.articulation.update(dt=0.0)

        # Get Jacobian for end effector
        jacobians = self.articulation.root_physx_view.get_jacobians()
        jacobian = jacobians[:, self.ee_jacobi_idx, :, self.joint_ids]

        # Get current end effector pose in world frame
        ee_pose_w = self.articulation.data.body_pose_w[:, self.ee_body_idx]
        ee_pos_w = ee_pose_w[:, 0:3]
        ee_quat_w = ee_pose_w[:, 3:7]

        # Convert EE pose to robot base frame
        ee_pos_b, ee_quat_b = subtract_frame_transforms(
            self.robot_base_pos,
            self.robot_base_quat,
            ee_pos_w,
            ee_quat_w,
        )

        # Get current joint positions for controlled joints
        all_joint_pos = self.articulation.data.joint_pos
        joint_pos = all_joint_pos[:, self.joint_ids]

        # Compute IK solution
        joint_pos_des = self.controller.compute(
            ee_pos_b,
            ee_quat_b,
            jacobian,
            joint_pos,
        )

        # Check for valid solution (no NaN values)
        success = not torch.isnan(joint_pos_des).any()

        # Convert result to numpy
        result_joints = joint_pos_des.squeeze(0).cpu().numpy()

        return result_joints, success

    def reset(self):
        """Reset the controller state.

        Call this when starting a new motion sequence.
        """
        self.controller.reset()
