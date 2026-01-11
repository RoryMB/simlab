"""Configuration classes and path utilities for robot modules."""

from dataclasses import dataclass
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
ASSETS_ROOT = PROJECT_ROOT / "assets"


def get_asset_path(relative_path: str) -> str:
    """Get absolute path to an asset file.

    Args:
        relative_path: Path relative to the assets directory

    Returns:
        Absolute path as a string
    """
    return str(ASSETS_ROOT / relative_path)


@dataclass
class PhysicsConfig:
    """Physics simulation parameters.

    Default values are tuned for laboratory robotics simulation.
    """
    contact_offset: float = 0.0001
    """Contact offset for collision detection (meters)"""

    contact_threshold: float = 0.0
    """Contact threshold for collision events"""

    raycast_distance: float = 0.03
    """Default raycast distance for gripper detection (meters)"""

    motion_position_threshold: float = 0.01
    """Position threshold for motion completion detection"""

    motion_velocity_threshold: float = 0.008
    """Velocity threshold for motion completion detection"""


# Default physics configuration
DEFAULT_PHYSICS_CONFIG = PhysicsConfig()
