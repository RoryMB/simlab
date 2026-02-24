"""Configuration classes for motion approaches.

Provides dataclasses for loading and storing motion configuration
from YAML files. Each robot can have its own motion_config.yaml
specifying default approach, enabled approaches, and execution settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ApproachConfig:
    """Configuration for a single motion approach.

    Attributes:
        enabled: Whether this approach is available for use
        config_path: Path to approach-specific config file (relative to robot config dir)
        trajectory_generator: For IK-only approaches, which trajectory generator to pair with
    """

    enabled: bool = False
    config_path: str = None
    trajectory_generator: str = None


@dataclass
class ExecutionConfig:
    """Configuration for motion execution.

    Attributes:
        default_mode: Default execution mode ("teleport", "pd_follow")
        convergence_threshold: Thresholds for motion completion
        trajectory_timestep: Timestep for trajectory waypoint stepping (seconds)
    """

    default_mode: str = "pd_follow"
    convergence_threshold: dict[str, float] = field(
        default_factory=lambda: {
            "position": 0.003,  # radians
            "velocity": 0.008,  # rad/s
        },
    )
    trajectory_timestep: float = 0.01  # 100Hz


@dataclass
class MotionConfig:
    """Complete motion configuration for a robot.

    Loaded from per-robot motion_config.yaml files.

    Attributes:
        default_approach: Name of approach to use when not specified in command
        fallback_approach: Approach to use if default fails or is unavailable
        approaches: Configuration for each available approach
        execution: Execution settings (modes, thresholds)
    """

    default_approach: str = "differential_ik"
    fallback_approach: str = None
    approaches: dict[str, ApproachConfig] = field(default_factory=dict)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "MotionConfig":
        """Load configuration from a YAML file.

        Args:
            yaml_path: Path to the motion_config.yaml file

        Returns:
            MotionConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file does not exist
            yaml.YAMLError: If config file is invalid YAML
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Motion config not found: {yaml_path}")

        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        motion_data = data.get("motion", {})

        # Parse approaches
        approaches = {}
        for name, approach_data in motion_data.get("approaches", {}).items():
            if approach_data is None:
                approach_data = {}
            approaches[name] = ApproachConfig(
                enabled=approach_data.get("enabled", False),
                config_path=approach_data.get("config_path"),
                trajectory_generator=approach_data.get("trajectory_generator"),
            )

        # Parse execution config
        exec_data = motion_data.get("execution", {})
        convergence = exec_data.get("convergence_threshold", {})
        execution = ExecutionConfig(
            default_mode=exec_data.get("default_mode", "pd_follow"),
            convergence_threshold={
                "position": convergence.get("position", 0.003),
                "velocity": convergence.get("velocity", 0.008),
            },
            trajectory_timestep=exec_data.get("trajectory_timestep", 0.01),
        )

        return cls(
            default_approach=motion_data.get("default_approach", "differential_ik"),
            fallback_approach=motion_data.get("fallback_approach"),
            approaches=approaches,
            execution=execution,
        )

    def get_approach_config(self, approach_name: str) -> Optional[ApproachConfig]:
        """Get configuration for a specific approach.

        Args:
            approach_name: Name of the approach

        Returns:
            ApproachConfig if found and enabled, None otherwise
        """
        config = self.approaches.get(approach_name)
        if config and config.enabled:
            return config
        return None
