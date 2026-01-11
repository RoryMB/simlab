"""Configuration classes and path utilities for robot modules."""

from dataclasses import dataclass
from pathlib import Path

from isaacsim.storage.native import get_assets_root_path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
CUSTOM_ASSETS_ROOT_PATH = PROJECT_ROOT / "assets"
NVIDIA_ASSETS_ROOT_PATH = get_assets_root_path()
# if NVIDIA_ASSETS_ROOT_PATH is None:
#     print("Error: Could not find Isaac Sim assets folder")
#     simulation_app.close()
#     sys.exit()


def get_custom_asset_path(relative_path: str) -> str:
    """Get absolute path to a custom asset file.

    Args:
        relative_path: Path relative to the custom assets directory

    Returns:
        Absolute path as a string
    """
    return str(CUSTOM_ASSETS_ROOT_PATH / relative_path)


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
