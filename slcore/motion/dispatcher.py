"""Motion dispatcher for routing commands to appropriate approaches.

The MotionDispatcher is the main entry point for motion commands. It:
1. Resolves which approach to use (explicit, default, or fallback)
2. Validates that the approach has required capabilities
3. Dispatches to the selected approach
"""

from typing import Optional

import numpy as np

from slcore.motion.base import (
    CapabilityError,
    MotionApproach,
    MotionResult,
)
from slcore.motion.capabilities import MotionCapability
from slcore.motion.config import MotionConfig


class MotionDispatcher:
    """Routes motion commands to appropriate approaches.

    The dispatcher maintains a registry of available approaches and
    handles approach selection, capability validation, and dispatching.

    Attributes:
        config: Motion configuration loaded from YAML
        approaches: Registry of approach name -> MotionApproach instance
    """

    def __init__(self, config: MotionConfig):
        """Initialize the motion dispatcher.

        Args:
            config: Motion configuration specifying defaults and enabled approaches
        """
        self.config = config
        self.approaches: dict[str, MotionApproach] = {}

    def register_approach(self, name: str, approach: MotionApproach):
        """Register a motion approach.

        Args:
            name: Name to register the approach under (must match config)
            approach: The approach instance

        Raises:
            ValueError: If approach with this name is already registered
        """
        if name in self.approaches:
            raise ValueError(f"Approach '{name}' is already registered")
        self.approaches[name] = approach
        print(f"Registered motion approach: {name} (capabilities: {approach.capabilities()})")

    def get_approach(self, name: str) -> Optional[MotionApproach]:
        """Get a registered approach by name.

        Args:
            name: Approach name

        Returns:
            The approach instance, or None if not found
        """
        return self.approaches.get(name)

    def resolve_approach(self, explicit: str = None) -> tuple[str, MotionApproach]:
        """Resolve which approach to use.

        Resolution order:
        1. Explicit approach specified in command
        2. Default approach from config
        3. Fallback approach from config

        Args:
            explicit: Explicitly requested approach name, or None

        Returns:
            Tuple of (approach_name, approach_instance)

        Raises:
            ValueError: If no valid approach can be resolved
        """
        candidates = []

        # Build candidate list in priority order
        if explicit:
            candidates.append(("explicit", explicit))
        if self.config.default_approach:
            candidates.append(("default", self.config.default_approach))
        if self.config.fallback_approach:
            candidates.append(("fallback", self.config.fallback_approach))

        # Try each candidate
        for source, name in candidates:
            # Check if approach is registered
            approach = self.approaches.get(name)
            if approach is None:
                continue

            # Check if approach is enabled in config
            approach_config = self.config.get_approach_config(name)
            if approach_config is None:
                continue

            return name, approach

        # No valid approach found
        requested = explicit or self.config.default_approach or "(none)"
        registered = list(self.approaches.keys())
        raise ValueError(
            f"No valid approach found. Requested: {requested}, "
            f"Registered: {registered}"
        )

    def validate_capabilities(
        self,
        approach: MotionApproach,
        required: MotionCapability,
    ):
        """Validate that approach has required capabilities.

        Args:
            approach: The approach to validate
            required: Required capabilities

        Raises:
            CapabilityError: If approach is missing required capabilities
        """
        if required == MotionCapability.NONE:
            return

        available = approach.capabilities()
        if not approach.has_capability(required):
            raise CapabilityError(required=required, available=available)

    def compute_motion(
        self,
        target_position: np.ndarray,
        target_orientation: np.ndarray,
        approach: str = None,
        linear_path: bool = False,
        collision_check: bool = False,
        **kwargs,
    ) -> MotionResult:
        """Compute motion to reach target pose.

        This is the main entry point for motion commands.

        Args:
            target_position: Target position [x, y, z] in world frame (meters)
            target_orientation: Target orientation quaternion [w, x, y, z]
            approach: Explicit approach name, or None for default
            linear_path: If True, requires LINEAR_CARTESIAN capability
            collision_check: If True, requires COLLISION_AWARE capability
            **kwargs: Additional parameters passed to the approach

        Returns:
            MotionResult containing computed joint positions or trajectory

        Raises:
            ValueError: If no valid approach can be resolved
            CapabilityError: If required capabilities are not available
            IKError: If IK fails to find a solution
        """
        # Resolve approach
        approach_name, approach_instance = self.resolve_approach(approach)

        # Determine required capabilities
        required = MotionCapability.IK  # Always need IK
        if linear_path:
            required |= MotionCapability.LINEAR_CARTESIAN
        if collision_check:
            required |= MotionCapability.COLLISION_AWARE

        # Validate capabilities (strict mode - fail if missing)
        self.validate_capabilities(approach_instance, required)

        # Dispatch to approach
        return approach_instance.compute_motion(
            target_position=target_position,
            target_orientation=target_orientation,
            **kwargs,
        )

    def reset(self, approach: str = None):
        """Reset approach state.

        Args:
            approach: Specific approach to reset, or None for all
        """
        if approach:
            if approach in self.approaches:
                self.approaches[approach].reset()
        else:
            for a in self.approaches.values():
                a.reset()
