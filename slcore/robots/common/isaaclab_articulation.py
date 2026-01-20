"""PhysX ArticulationView wrapper for accessing Jacobians.

This module provides utilities to create PhysX ArticulationView objects directly
from existing USD prims in the scene. This allows accessing physics data (like
Jacobians) needed for differential IK without requiring full Isaac Lab
Articulation initialization.

NOTE: This module uses Isaac Sim's core APIs which are only available after
Isaac Sim has started. All imports are deferred to function call time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import omni.physics.tensors.impl.api as physx


@dataclass
class ArticulationViewWrapper:
    """Lightweight wrapper around PhysX ArticulationView.

    This wrapper provides a minimal interface compatible with Isaac Lab's
    differential IK controller, without requiring full Articulation
    initialization.

    Attributes:
        root_physx_view: The underlying PhysX ArticulationView for Jacobian access
        is_fixed_base: Whether this is a fixed-base or floating-base articulation
        data: Articulation data accessor with joint/body names and state
    """

    root_physx_view: physx.ArticulationView
    is_fixed_base: bool
    data: ArticulationDataAccessor


@dataclass
class ArticulationDataAccessor:
    """Minimal data accessor for articulation state.

    Provides access to joint/body names and state tensors needed for IK.
    """

    joint_names: list[str]
    body_names: list[str]
    _view: physx.ArticulationView
    _device: str = "cuda:0"

    @property
    def joint_pos(self):
        """Get current joint positions as tensor."""
        import torch
        positions = self._view.get_dof_positions()  # numpy array
        return torch.as_tensor(positions, device=self._device)

    @property
    def body_pose_w(self):
        """Get body poses in world frame [pos(3), quat(4)].

        PhysX returns quaternions as [x, y, z, w], but Isaac Lab expects [w, x, y, z].
        This property converts to wxyz order.
        """
        import torch
        transforms = self._view.get_link_transforms()  # Shape: (num_envs * num_links, 7), numpy array
        num_links = len(self.body_names)
        # Convert to PyTorch tensor and reshape to (num_envs, num_links, 7)
        transforms_tensor = torch.as_tensor(transforms, device=self._device, dtype=torch.float32)
        poses = transforms_tensor.reshape(-1, num_links, 7)
        # Convert quaternion from xyzw to wxyz order
        # Input: [pos(3), x, y, z, w] -> Output: [pos(3), w, x, y, z]
        poses_wxyz = torch.cat([
            poses[..., :3],  # position (xyz)
            poses[..., 6:7],  # w
            poses[..., 3:6],  # xyz
        ], dim=-1)
        return poses_wxyz


def create_articulation_from_prim(
    prim_path: str,
    device: str = "cuda:0",
) -> ArticulationViewWrapper:
    """Create a PhysX ArticulationView wrapper from an existing USD prim.

    This creates a lightweight wrapper around PhysX's ArticulationView that
    provides access to Jacobians and articulation state without requiring
    full Isaac Lab Articulation initialization.

    Args:
        prim_path: USD prim path of the existing articulation root
        device: Torch device for tensor computations (default: "cuda:0")

    Returns:
        ArticulationViewWrapper with access to Jacobians and state

    Example:
        >>> wrapper = create_articulation_from_prim("/World/env_0/pf400")
        >>> jacobians = wrapper.root_physx_view.get_jacobians()
        >>> joint_names = wrapper.data.joint_names
    """
    # Deferred import - only available after Isaac Sim starts
    from isaacsim.core.simulation_manager import SimulationManager

    # Get the physics simulation view
    physics_sim_view = SimulationManager.get_physics_sim_view()

    # Create ArticulationView for this prim
    # Note: Isaac Sim uses * instead of .* for glob patterns
    articulation_view = physics_sim_view.create_articulation_view(prim_path)

    # Check if the backend was properly initialized
    if articulation_view._backend is None:
        raise RuntimeError(
            f"Failed to create ArticulationView for '{prim_path}'. "
            "Ensure physics simulation is running."
        )

    # Get articulation metadata
    metatype = articulation_view.shared_metatype
    is_fixed_base = metatype.fixed_base
    joint_names = list(metatype.dof_names)
    body_names = list(metatype.link_names)

    # Create data accessor
    data = ArticulationDataAccessor(
        joint_names=joint_names,
        body_names=body_names,
        _view=articulation_view,
        _device=device,
    )

    # Create and return wrapper
    return ArticulationViewWrapper(
        root_physx_view=articulation_view,
        is_fixed_base=is_fixed_base,
        data=data,
    )
