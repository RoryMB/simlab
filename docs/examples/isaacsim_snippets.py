"""Isaac Sim Code Snippets - Reference Only

This file contains code snippets for common Isaac Sim operations.
DO NOT RUN THIS FILE - it is for reference only.
The code blocks show the easiest ways to accomplish common tasks.
"""

# =============================================================================
# SimulationApp Initialization - CRITICAL
# =============================================================================

# SimulationApp MUST be created before importing ANY other Isaac Sim modules
# This is required for all Isaac Sim scripts
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": False})  # or {"headless": True} for headless mode

# Only after simulation_app is created can you import other Isaac Sim modules
# Example of proper import order:
# from isaacsim import SimulationApp
# simulation_app = SimulationApp({"headless": False})
# from isaacsim.core.api import World
# from isaacsim.core.api.robots import Robot
# etc.

# =============================================================================
# Basic Prim Operations
# =============================================================================

# Get a USD prim by path
import omni.usd
stage = omni.usd.get_context().get_stage()
prim = stage.GetPrimAtPath(prim_path)

# Check if a prim exists and is valid
# Returns: True if prim exists and is valid, False otherwise
is_valid = prim.IsValid()

# =============================================================================
# Pose and Transform Conversions
# =============================================================================

# Convert pose to 4x4 homogeneous transform matrix
# position: [x, y, z] position
# orientation: [w, x, y, z] quaternion
from isaacsim.core.utils.transformations import tf_matrix_from_pose
transform_matrix = tf_matrix_from_pose(position, orientation)

# Convert 4x4 transform matrix to pose
# transform: 4x4 homogeneous transformation matrix
# Returns: (position, orientation) arrays
from isaacsim.core.utils.transformations import pose_from_tf_matrix
position, orientation = pose_from_tf_matrix(transform)

# =============================================================================
# Stage and Units
# =============================================================================

# Get the current stage units scale factor
# Returns: Scale factor from stage units to meters
from isaacsim.core.utils.stage import get_stage_units
scale = get_stage_units()

# =============================================================================
# Rotation Conversions
# =============================================================================

# Convert Euler angles to quaternion
# roll, pitch, yaw: Rotation around x, y, z axes (radians)
# Returns: Quaternion [w, x, y, z]
import numpy as np
from isaacsim.core.utils.rotations import euler_angles_to_quat
quaternion = euler_angles_to_quat(np.array([roll, pitch, yaw]))

# Convert quaternion to Euler angles
# quaternion: [w, x, y, z] quaternion
# Returns: [roll, pitch, yaw] in radians
from isaacsim.core.utils.rotations import quat_to_euler_angles
euler = quat_to_euler_angles(quaternion)
roll, pitch, yaw = euler[0], euler[1], euler[2]
