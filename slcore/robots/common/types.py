"""Common type definitions for robot modules."""

from enum import Enum


class CoordinateType(Enum):
    """Coordinate type for robot movement commands."""
    JOINT_ANGLES = "joint_angles"
    CARTESIAN = "cartesian"
