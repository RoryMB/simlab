from typing import Optional

import numpy as np
import omni.usd
from pxr import UsdGeom, UsdPhysics

from isaacsim.core.api.robots import Robot
from isaacsim.core.prims import SingleXFormPrim
from isaacsim.core.utils.transformations import (
    get_relative_transform,
    get_world_pose_from_relative,
    pose_from_tf_matrix,
    tf_matrix_from_pose,
)


# =============================================================================
# Coordinate System Utilities
# =============================================================================

def get_prim_world_pose(prim) -> tuple[np.ndarray, np.ndarray]:
    """Get world pose of a prim.

    Args:
        prim: USD prim object

    Returns:
        Tuple of (position, orientation) where:
        - position: [x, y, z] in world frame
        - orientation: [w, x, y, z] quaternion in world frame
    """
    # Use Isaac Sim's existing SingleXFormPrim for consistent API
    prim_wrapper = SingleXFormPrim(prim_path=str(prim.GetPath()))
    return prim_wrapper.get_world_pose()


def set_prim_world_pose(
    prim,
    position: Optional[np.ndarray] = None,
    orientation: Optional[np.ndarray] = None,
) -> None:
    """Set world pose of a prim.

    Args:
        prim: USD prim object
        position: [x, y, z] position in world frame (optional)
        orientation: [w, x, y, z] quaternion in world frame (optional)
    """
    prim_wrapper = SingleXFormPrim(prim_path=str(prim.GetPath()))
    prim_wrapper.set_world_pose(position=position, orientation=orientation)


def get_relative_pose(prim, relative_to_prim) -> tuple[np.ndarray, np.ndarray]:
    """Get pose of one prim relative to another prim.

    Args:
        prim: USD prim object (source)
        relative_to_prim: USD prim object (reference)

    Returns:
        Tuple of (position, orientation) of source relative to target
    """
    # Get relative transform matrix using Isaac Sim's existing function
    transform_matrix = get_relative_transform(prim, relative_to_prim)

    # Extract pose from transform matrix
    return pose_from_tf_matrix(transform_matrix)


def world_to_local_coords(relative_to_prim, world_position: np.ndarray, world_orientation: Optional[np.ndarray] = None) -> tuple[np.ndarray, np.ndarray]:
    """Convert world coordinates to local coordinates relative to a reference prim.

    Args:
        relative_to_prim: USD prim object for reference frame
        world_position: [x, y, z] position in world frame
        world_orientation: [w, x, y, z] quaternion orientation in world frame (optional, defaults to identity)

    Returns:
        Tuple of (local_position, local_orientation) relative to the reference prim
    """
    if world_orientation is None:
        world_orientation = np.array([1.0, 0.0, 0.0, 0.0])  # Identity quaternion

    # Get world-to-local transform matrix
    stage = omni.usd.get_context().get_stage()
    world_prim = stage.GetPseudoRoot()  # World root
    world_to_local_transform = get_relative_transform(world_prim, relative_to_prim)

    # Convert world pose to transform matrix
    world_to_world_transform = tf_matrix_from_pose(world_position, world_orientation)

    # Chain the transformations: world pose -> local frame
    world_to_local_pose_transform = world_to_local_transform @ world_to_world_transform

    # Extract local pose
    return pose_from_tf_matrix(world_to_local_pose_transform)


def local_to_world_coords(relative_to_prim, local_position: np.ndarray, local_orientation: Optional[np.ndarray] = None) -> tuple[np.ndarray, np.ndarray]:
    """Convert local coordinates to world coordinates.

    Args:
        relative_to_prim: USD prim object whose frame defines local coords
        local_position: [x, y, z] position in local frame
        local_orientation: [w, x, y, z] quaternion orientation in local frame (optional, defaults to identity)

    Returns:
        Tuple of (world_position, world_orientation) in world frame
    """
    if local_orientation is None:
        local_orientation = np.array([1.0, 0.0, 0.0, 0.0])  # Identity quaternion

    # Use Isaac Sim's existing function
    return get_world_pose_from_relative(relative_to_prim, local_position, local_orientation)


# =============================================================================
# Prim Manipulation Utilities
# =============================================================================

def find_prim_by_name(name: str, search_root_prim: str = "/World") -> Optional[str]:
    """Find a prim by name within search root.

    Args:
        name: Name to search for
        search_root: Root path to search within

    Returns:
        Full prim path if found, None otherwise
    """
    def _recursive_search(prim):
        if prim.GetName() == name:
            return str(prim.GetPath())

        for child in prim.GetChildren():
            result = _recursive_search(child)
            if result:
                return result
        return None

    return _recursive_search(search_root_prim)


def get_prim_bounds(prim) -> tuple[np.ndarray, np.ndarray]:
    """Get bounding box of a prim.

    Args:
        prim: USD prim object

    Returns:
        Tuple of (min_bounds, max_bounds) as [x, y, z] arrays

    Raises:
        ValueError: If prim bounds cannot be computed
    """
    if prim and prim.IsA(UsdGeom.Boundable):
        boundable = UsdGeom.Boundable(prim)
        extent = boundable.GetExtentAttr().Get()
        if extent:
            min_bounds = np.array(extent[0])
            max_bounds = np.array(extent[1])
            return min_bounds, max_bounds

    raise ValueError(f"Cannot compute bounds for prim at {prim.GetPath()}")


def list_child_prims(parent_prim) -> list[str]:
    """List all child prim paths directly under a parent.

    Args:
        parent_prim: USD prim object

    Returns:
        List of child prim paths
    """
    child_paths = []
    for child in parent_prim.GetChildren():
        child_paths.append(str(child.GetPath()))

    return child_paths


# =============================================================================
# Physics Utilities
# =============================================================================

def add_collider_to_prim(prim, approximation_type: str = "convexHull") -> None:
    """Add a collider to a prim.

    This function adds colliders to geometry prims (Cube, Sphere, Mesh, etc.)
    without adding rigid body dynamics, making them static collision objects.

    Args:
        prim: USD prim object to add collision to
        approximation_type: Collision approximation type for meshes
                          ("convexHull", "convexDecomposition", "boundingCube", etc.)

    Raises:
        ValueError: If prim is invalid or not a geometry prim
    """
    # Check if prim is a geometry prim (Cube, Sphere, Mesh, etc.)
    if not (prim.IsA(UsdGeom.Gprim) or prim.IsA(UsdGeom.Mesh)):
        raise ValueError(f"Prim at {prim.GetPath()} is not a geometry prim")

    # Apply collision API if not already present
    if not prim.HasAPI(UsdPhysics.CollisionAPI):
        collision_api = UsdPhysics.CollisionAPI.Apply(prim)
    else:
        collision_api = UsdPhysics.CollisionAPI(prim)

    # Enable collision
    collision_api.CreateCollisionEnabledAttr(True)

    # For mesh prims, add mesh-specific collision properties
    if prim.IsA(UsdGeom.Mesh):
        if not prim.HasAPI(UsdPhysics.MeshCollisionAPI):
            mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
        else:
            mesh_collision_api = UsdPhysics.MeshCollisionAPI(prim)
        mesh_collision_api.CreateApproximationAttr().Set(approximation_type)


# =============================================================================
# Robot-Specific Utilities
# =============================================================================

def get_robot_end_effector_pose(robot: Robot) -> tuple[np.ndarray, np.ndarray]:
    """Get current end-effector pose using robot's kinematics.

    Args:
        robot: Isaac Sim Robot object

    Returns:
        Tuple of (position, orientation) where:
        - position: [x, y, z] in world frame
        - orientation: [w, x, y, z] quaternion in world frame

    Raises:
        RuntimeError: If robot kinematics solver is not available
    """
    # Check if robot has kinematics solver available
    if hasattr(robot, '_kinematics_solver') and robot._kinematics_solver is not None:
        # Use proper kinematics solver if available
        return robot._kinematics_solver.compute_end_effector_pose()
    else:
        raise RuntimeError("Robot kinematics solver not available. Initialize robot with kinematics solver.")
