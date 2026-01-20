"""Configuration classes and path utilities for robot modules."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
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


@dataclass
class DifferentialIKConfig:
    """Differential IK configuration parameters.

    Loaded from per-robot YAML configuration files.
    See assets/robots/<Manufacturer>/<Model>/isaacsim/differential_ik_config.yaml.
    """

    # IK solver settings
    ik_method: str = "dls"
    """IK method: "pinv", "svd", "trans", or "dls" (damped least-squares)"""

    lambda_val: float = 0.05
    """Damping factor for DLS method (higher = more stable, lower = faster)"""

    # Tolerances
    position_tolerance: float = 0.001
    """Position tolerance in meters"""

    orientation_tolerance: float = 0.01
    """Orientation tolerance in radians"""

    # Motion completion thresholds
    joint_diff_threshold: float = 0.003
    """Maximum joint position error for motion completion (radians)"""

    velocity_threshold: float = 0.008
    """Maximum joint velocity for motion completion (rad/s)"""

    # Home pose
    home_pose: list[float] = field(default_factory=lambda: [0.0] * 7)
    """Home joint positions (radians)"""

    # End effector
    end_effector_body_name: str = "pointer"
    """Name of the end effector body in the articulation"""

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "DifferentialIKConfig":
        """Load configuration from a YAML file.

        Args:
            yaml_path: Path to the differential_ik_config.yaml file

        Returns:
            DifferentialIKConfig instance with loaded values
        """
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls(
            ik_method=data.get("ik_method", "dls"),
            lambda_val=data.get("ik_params", {}).get("lambda_val", 0.05),
            position_tolerance=data.get("tolerances", {}).get("position", 0.001),
            orientation_tolerance=data.get("tolerances", {}).get("orientation", 0.01),
            joint_diff_threshold=data.get("motion_complete", {}).get("joint_diff_threshold", 0.003),
            velocity_threshold=data.get("motion_complete", {}).get("velocity_threshold", 0.008),
            home_pose=data.get("home_pose", [0.0] * 7),
            end_effector_body_name=data.get("end_effector", {}).get("body_name", "pointer"),
        )
