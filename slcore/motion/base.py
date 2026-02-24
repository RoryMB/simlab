"""Base classes for motion approaches.

Defines the MotionApproach abstract base class that all motion approaches
must implement, along with MotionResult for returning computed motions
and custom exceptions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from slcore.motion.capabilities import MotionCapability


class CapabilityError(Exception):
    """Raised when a required capability is not available.

    This error is raised when a motion command requests a feature
    (e.g., linear_path=True) but the selected approach does not
    have the required capability (e.g., LINEAR_CARTESIAN).
    """

    def __init__(
        self,
        required: MotionCapability,
        available: MotionCapability,
        message: str = None,
    ):
        self.required = required
        self.available = available
        self.missing = required & ~available
        if message is None:
            message = (
                f"Required capabilities {required} not available. "
                f"Missing: {self.missing}"
            )
        super().__init__(message)


class IKError(Exception):
    """Raised when inverse kinematics fails to find a solution.

    This error indicates that the IK solver could not find valid
    joint positions to achieve the requested pose.
    """

    def __init__(
        self,
        target_position: np.ndarray,
        target_orientation: np.ndarray,
        message: str = None,
    ):
        self.target_position = target_position
        self.target_orientation = target_orientation
        if message is None:
            message = (
                f"IK failed for position={target_position.tolist()}, "
                f"orientation={target_orientation.tolist()}"
            )
        super().__init__(message)


@dataclass
class MotionResult:
    """Result of a motion computation.

    Contains the computed joint positions or trajectory, along with
    success/failure status and optional error information.

    Attributes:
        success: True if motion was computed successfully
        joint_positions: Single joint configuration (for IK-only approaches)
        trajectory: List of (time, joint_positions) waypoints (for trajectory approaches)
        error_message: Description of failure if success is False
    """

    success: bool
    joint_positions: np.ndarray = None
    trajectory: list[tuple[float, np.ndarray]] = field(default_factory=list)
    error_message: str = None

    def __post_init__(self):
        """Validate that result contains appropriate data."""
        if self.success:
            if self.joint_positions is None and not self.trajectory:
                raise ValueError(
                    "Successful MotionResult must have joint_positions or trajectory"
                )


class MotionApproach(ABC):
    """Abstract base class for motion approaches.

    A motion approach computes how to move a robot from its current
    state to a target pose. Different approaches have different
    capabilities and trade-offs.

    Subclasses must implement:
        - capabilities(): Return the capabilities this approach provides
        - compute_motion(): Compute joint positions/trajectory for a target pose
        - reset(): Reset internal state for a new motion sequence

    Example:
        class MyApproach(MotionApproach):
            def capabilities(self) -> MotionCapability:
                return MotionCapability.IK | MotionCapability.VELOCITY_LIMITS

            def compute_motion(
                self,
                target_position: np.ndarray,
                target_orientation: np.ndarray,
                **kwargs,
            ) -> MotionResult:
                # Compute IK solution
                joints = self._solve_ik(target_position, target_orientation)
                return MotionResult(success=True, joint_positions=joints)

            def reset(self):
                pass
    """

    @abstractmethod
    def capabilities(self) -> MotionCapability:
        """Return the capabilities this approach provides.

        Returns:
            MotionCapability flags indicating supported features
        """
        pass

    @abstractmethod
    def compute_motion(
        self,
        target_position: np.ndarray,
        target_orientation: np.ndarray,
        **kwargs,
    ) -> MotionResult:
        """Compute motion to reach target pose.

        Args:
            target_position: Target position [x, y, z] in world frame (meters)
            target_orientation: Target orientation quaternion [w, x, y, z]
            **kwargs: Additional approach-specific parameters

        Returns:
            MotionResult containing computed joint positions or trajectory

        Raises:
            IKError: If IK fails to find a solution
            CapabilityError: If required capability is not available
        """
        pass

    @abstractmethod
    def reset(self):
        """Reset approach state for a new motion sequence.

        Call this when starting a new motion command to clear any
        internal state from previous computations.
        """
        pass

    def has_capability(self, capability: MotionCapability) -> bool:
        """Check if this approach has a specific capability.

        Args:
            capability: The capability to check for

        Returns:
            True if the approach has the capability
        """
        return (capability & self.capabilities()) == capability
