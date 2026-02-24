"""Motion capability flags for approach selection and validation.

Capabilities describe what features a motion approach provides. The dispatcher
uses these to validate that requested features are available before executing
a motion command.
"""

from enum import Flag, auto


class MotionCapability(Flag):
    """Capabilities that motion approaches may provide.

    These flags can be combined using bitwise operations to express
    the full set of capabilities an approach offers.

    Example:
        >>> approach_caps = MotionCapability.IK | MotionCapability.VELOCITY_LIMITS
        >>> required = MotionCapability.IK
        >>> (required & approach_caps) == required
        True
    """

    NONE = 0
    """No capabilities (for initialization)"""

    IK = auto()
    """Inverse kinematics: pose -> joint angles"""

    TRAJECTORY = auto()
    """Generates timed waypoint sequences"""

    COLLISION_AWARE = auto()
    """Considers obstacles during planning"""

    REACTIVE = auto()
    """Replans every simulation timestep"""

    LINEAR_CARTESIAN = auto()
    """Can constrain end-effector to linear path"""

    VELOCITY_LIMITS = auto()
    """Respects per-joint velocity constraints"""

    ACCEL_LIMITS = auto()
    """Respects per-joint acceleration constraints"""

    JERK_LIMITS = auto()
    """Respects per-joint jerk constraints"""
