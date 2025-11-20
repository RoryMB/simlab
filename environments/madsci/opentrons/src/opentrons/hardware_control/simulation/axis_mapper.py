"""
Axis mapping between Opentrons hardware axes and simulation joints.
"""

import logging
from typing import Dict, List, Any
from opentrons.types import Mount

logger = logging.getLogger(__name__)


class AxisMapper:
    """Maps Opentrons hardware axes to simulation joint commands."""

    # Mapping from Opentrons axis names to simulation joints
    AXIS_TO_JOINT_MAPPING = {
        "X": "pipette_casing_joint",    # X-axis gantry movement (0-418mm)
        "Y": "pipette_rail_joint",      # Y-axis gantry movement (0-353mm)
        "Z": "pipette_left_joint",      # Left mount Z-axis (0-218mm)
        "A": "pipette_right_joint",     # Right mount Z-axis (0-218mm)
        "B": "left_plunger_joint",      # Left mount plunger (0-19mm)
        "C": "right_plunger_joint",     # Right mount plunger (0-19mm)
    }

    # Joint limits in meters (matching your joint descriptions)
    JOINT_LIMITS = {
        "pipette_rail_joint": (0.0, 0.353),       # Y-axis
        "pipette_casing_joint": (0.0, 0.418),     # X-axis
        "pipette_left_joint": (-0.218, 0.0),      # Left Z (inverted)
        "pipette_right_joint": (-0.218, 0.0),     # Right Z (inverted)
        "left_plunger_joint": (0.0, 0.019),       # Left plunger
        "right_plunger_joint": (0.0, 0.019),      # Right plunger
    }

    # Opentrons home positions in mm
    OPENTRONS_HOME_POSITIONS = {
        "X": 418.0,    # X-axis home (right)
        "Y": 353.0,    # Y-axis home (back)
        "Z": 218.0,    # Left Z home (top)
        "A": 218.0,    # Right Z home (top)
        "B": 19.0,     # Left plunger home
        "C": 19.0,     # Right plunger home
    }

    def __init__(self):
        """Initialize the axis mapper."""
        self.current_positions = {}  # Track current positions

    def convert_positions_to_joints(self, target_positions: Dict[str, float]) -> List[Dict[str, Any]]:
        """Convert Opentrons axis positions to joint commands.

        Args:
            target_positions: Dictionary mapping axis names to positions in mm

        Returns:
            List of joint command dictionaries for simulation
        """
        joint_commands = []

        for axis_name, position_mm in target_positions.items():
            if axis_name not in self.AXIS_TO_JOINT_MAPPING:
                logger.warning(f"Unknown axis: {axis_name}")
                continue

            joint_name = self.AXIS_TO_JOINT_MAPPING[axis_name]
            joint_position = self._convert_axis_to_joint_position(axis_name, position_mm)

            # Validate joint limits
            if joint_name in self.JOINT_LIMITS:
                min_pos, max_pos = self.JOINT_LIMITS[joint_name]
                if joint_position < min_pos or joint_position > max_pos:
                    logger.error(
                        f"Joint position {joint_position:.4f} out of bounds for {joint_name} "
                        f"[{min_pos}, {max_pos}]"
                    )
                    continue

            joint_commands.append({
                "joint": joint_name,
                "target_position": joint_position
            })

            # Update tracked position
            self.current_positions[axis_name] = position_mm

        return joint_commands

    def _convert_axis_to_joint_position(self, axis_name: str, position_mm: float) -> float:
        """Convert a single axis position to joint position.

        Args:
            axis_name: Opentrons axis name (X, Y, Z, A, B, C)
            position_mm: Position in millimeters

        Returns:
            Joint position in meters
        """
        position_m = position_mm / 1000.0  # Convert to meters

        if axis_name == "X":
            # X-axis: 0-418mm maps to 0-0.418m joint range
            return position_m

        elif axis_name == "Y":
            # Y-axis: 0-353mm maps to 0-0.353m joint range
            return position_m

        elif axis_name in ["Z", "A"]:
            # Z-axes: Opentrons coordinates are inverted from joint coordinates
            # Opentrons: 0mm (bottom) to 218mm (top/home)
            # Joint: 0m (home/top) to -0.218m (bottom)
            return -position_m

        elif axis_name in ["B", "C"]:
            # Plunger axes: 0-19mm maps to 0-0.019m joint range
            return position_m

        else:
            logger.warning(f"Unknown axis conversion: {axis_name}")
            return position_m

    def get_home_joint_commands(self) -> List[Dict[str, Any]]:
        """Get joint commands to move robot to home position.

        Returns:
            List of joint commands for homing
        """
        return self.convert_positions_to_joints(self.OPENTRONS_HOME_POSITIONS)

    def mount_to_axis_mapping(self, mount: Mount) -> Dict[str, str]:
        """Get axis mappings for a specific mount.

        Args:
            mount: Mount object (LEFT or RIGHT)

        Returns:
            Dictionary mapping axis types to axis names for this mount
        """
        if mount == Mount.LEFT:
            return {
                "z_axis": "Z",
                "plunger_axis": "B"
            }
        else:  # Mount.RIGHT
            return {
                "z_axis": "A",
                "plunger_axis": "C"
            }

    def get_mount_axis_position(self, mount: Mount, axis_type: str) -> float:
        """Get current position of a mount's axis.

        Args:
            mount: Mount object
            axis_type: Type of axis ("z_axis" or "plunger_axis")

        Returns:
            Current position in mm, or home position if unknown
        """
        axis_mapping = self.mount_to_axis_mapping(mount)
        axis_name = axis_mapping.get(axis_type)

        if axis_name:
            return self.current_positions.get(
                axis_name,
                self.OPENTRONS_HOME_POSITIONS[axis_name]
            )

        return 0.0

    def get_axis_name_for_mount(self, mount: Mount, axis_type: str) -> str:
        """Get the axis name for a mount and axis type.

        Args:
            mount: Mount object
            axis_type: Type of axis ("z_axis" or "plunger_axis")

        Returns:
            Axis name string
        """
        axis_mapping = self.mount_to_axis_mapping(mount)
        return axis_mapping.get(axis_type, "")

    def convert_joint_positions_to_axes(self, joint_positions: Dict[str, float]) -> Dict[str, float]:
        """Convert joint positions back to Opentrons axis positions.

        Args:
            joint_positions: Dictionary mapping joint names to positions in meters

        Returns:
            Dictionary mapping axis names to positions in mm
        """
        axis_positions = {}

        # Reverse mapping from joint names to axis names
        JOINT_TO_AXIS_MAPPING = {v: k for k, v in self.AXIS_TO_JOINT_MAPPING.items()}

        for joint_name, position_m in joint_positions.items():
            if joint_name not in JOINT_TO_AXIS_MAPPING:
                logger.warning(f"Unknown joint: {joint_name}")
                continue

            axis_name = JOINT_TO_AXIS_MAPPING[joint_name]
            axis_position = self._convert_joint_to_axis_position(axis_name, position_m)
            axis_positions[axis_name] = axis_position

            # Update tracked position
            self.current_positions[axis_name] = axis_position

        return axis_positions

    def _convert_joint_to_axis_position(self, axis_name: str, position_m: float) -> float:
        """Convert a single joint position to axis position.

        Args:
            axis_name: Opentrons axis name (X, Y, Z, A, B, C)
            position_m: Position in meters

        Returns:
            Axis position in millimeters
        """
        position_mm = position_m * 1000.0  # Convert to millimeters

        if axis_name == "X":
            # X-axis: 0-0.418m joint range maps to 0-418mm
            return position_mm

        elif axis_name == "Y":
            # Y-axis: 0-0.353m joint range maps to 0-353mm
            return position_mm

        elif axis_name in ["Z", "A"]:
            # Z-axes: Joint coordinates are inverted from Opentrons coordinates
            # Joint: 0m (home/top) to -0.218m (bottom)
            # Opentrons: 218mm (top/home) to 0mm (bottom)
            return -position_mm

        elif axis_name in ["B", "C"]:
            # Plunger axes: 0-0.019m joint range maps to 0-19mm
            return position_mm

        else:
            logger.warning(f"Unknown axis conversion: {axis_name}")
            return position_mm