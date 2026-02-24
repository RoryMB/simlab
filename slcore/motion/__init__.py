"""Motion planning and execution framework for Simlab.

This module provides a unified interface for motion control across different
robots and algorithms. Key components:

- MotionCapability: Flags describing what features an approach provides
- MotionApproach: Abstract base class for motion algorithms
- MotionDispatcher: Routes commands to appropriate approaches
- MotionConfig: Configuration loading from YAML

Example usage:
    from slcore.motion import MotionDispatcher, MotionConfig
    from slcore.motion.approaches import DifferentialIKApproach

    # Load config and create dispatcher
    config = MotionConfig.from_yaml("path/to/motion_config.yaml")
    dispatcher = MotionDispatcher(config)

    # Register approaches
    diff_ik = DifferentialIKApproach(articulation, diff_ik_config)
    dispatcher.register_approach("differential_ik", diff_ik)

    # Compute motion
    result = dispatcher.compute_motion(
        target_position=np.array([0.5, 0.0, 0.3]),
        target_orientation=np.array([1.0, 0.0, 0.0, 0.0]),
    )
"""

from slcore.motion.base import (
    CapabilityError,
    IKError,
    MotionApproach,
    MotionResult,
)
from slcore.motion.capabilities import MotionCapability
from slcore.motion.config import ApproachConfig, ExecutionConfig, MotionConfig
from slcore.motion.dispatcher import MotionDispatcher

__all__ = [
    # Capabilities
    "MotionCapability",
    # Base classes
    "MotionApproach",
    "MotionResult",
    # Exceptions
    "CapabilityError",
    "IKError",
    # Config
    "MotionConfig",
    "ApproachConfig",
    "ExecutionConfig",
    # Dispatcher
    "MotionDispatcher",
]
