"""Configuration for parallel environment scaling."""

from dataclasses import dataclass

import numpy as np


@dataclass
class ParallelConfig:
    """Configuration for parallel environment execution.

    Defines how multiple workcell environments are spatially arranged
    and how they communicate with the multiplexed ZMQ ROUTER server.
    """

    num_envs: int = 5
    """Number of parallel environments to create"""

    spacing: float = 5.0
    """Distance between environments in meters"""

    zmq_port: int = 5555
    """Port for multiplexed ZMQ ROUTER server"""

    def get_offset(self, env_id: int) -> np.ndarray:
        """Calculate spatial offset for a given environment.

        Environments are arranged linearly along the X axis.

        Args:
            env_id: Environment ID (0 to num_envs-1)

        Returns:
            [x, y, z] offset in meters
        """
        return np.array([env_id * self.spacing, 0.0, 0.0])
