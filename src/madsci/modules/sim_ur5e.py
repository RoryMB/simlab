import argparse
import json
import os
import signal
import time
from enum import Enum
from typing import Annotated, Optional, Union

import numpy as np
import zmq

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from ur_interface.ur_kinematics import get_pose_from_joint_angles


class CoordinateType(Enum):
    """Supported coordinate system types."""
    JOINT_ANGLES = "joint_angles"
    CARTESIAN = "cartesian"


def validate_ur5e_joints(joints: list) -> bool:
    """Validate UR5e joint angles are within standard limits."""
    if len(joints) != 6:
        return False

    # UR5e joint limits (radians)
    joint_limits = [
        (-2*np.pi, 2*np.pi),
        (-2*np.pi, 2*np.pi),
        (-np.pi, np.pi),
        (-2*np.pi, 2*np.pi),
        (-2*np.pi, 2*np.pi),
        (-2*np.pi, 2*np.pi)
    ]

    for joint, (min_val, max_val) in zip(joints, joint_limits):
        if not (min_val <= joint <= max_val):
            return False
    return True


def simple_inverse_kinematics(pose: list) -> list:
    """Simple inverse kinematics for UR5e (basic analytical solution)."""
    if len(pose) != 6:
        raise ValueError("Expected 6-element pose [x, y, z, rx, ry, rz]")

    x, y, z, rx, ry, rz = pose

    # UR5e DH d parameters for calculations
    d1 = 0.1625

    # Base joint (rotation around z-axis)
    q1 = np.arctan2(y, x)

    # Distance in xy plane
    r = np.sqrt(x**2 + y**2)

    # Simplified calculation for remaining joints
    q2 = -np.pi/2 + np.arctan2(z - d1, r)
    q3 = 0.0  # Simplified
    q4 = -(q2 + q3) + ry  # Wrist alignment
    q5 = 0.0  # Simplified
    q6 = rz - q1  # End-effector orientation

    joints = [q1, q2, q3, q4, q5, q6]

    # Apply joint limits
    joint_limits = [
        (-2*np.pi, 2*np.pi),
        (-2*np.pi, 2*np.pi),
        (-np.pi, np.pi),
        (-2*np.pi, 2*np.pi),
        (-2*np.pi, 2*np.pi),
        (-2*np.pi, 2*np.pi)
    ]

    for i, (joint, (min_val, max_val)) in enumerate(zip(joints, joint_limits)):
        joints[i] = np.clip(joint, min_val, max_val)

    return joints


class SimUR5eInterface:
    """A robot interface that communicates via ZMQ."""

    status_code: int = 0
    device_number: int = 0

    def __init__(
        self,
        device_number: int = 0,
        zmq_server_url: str = "tcp://localhost:5555",
        logger: Optional[EventClient] = None,
        coordinate_type: CoordinateType = CoordinateType.JOINT_ANGLES,
        robot_model: str = "UR5e"
    ) -> "SimUR5eInterface":
        """Initialize the robot ZMQ client."""
        self.logger = logger or EventClient()
        self.device_number = device_number
        self.zmq_server_url = zmq_server_url
        self.coordinate_type = coordinate_type
        self.robot_model = robot_model

        # Validate robot model
        if robot_model.upper() != "UR5E":
            raise ValueError(f"Unsupported robot model: {robot_model}. Only UR5E is supported.")

        # Initialize ZMQ client
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.zmq_server_url)

        self.logger.log(f"SimUR5eInterface connected to ZMQ server at {self.zmq_server_url}")
        self.logger.log(f"Coordinate system: {self.coordinate_type.value}, Robot model: {self.robot_model}")

    def __del__(self):
        """Clean up ZMQ resources."""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()

    def send_zmq_command(self, command: dict) -> dict:
        """Send a command via ZMQ and return the response."""
        try:
            # Send command
            self.socket.send_string(json.dumps(command))

            # Receive response
            response_str = self.socket.recv_string()
            response = json.loads(response_str)

            return response
        except Exception as e:
            self.logger.log(f"ZMQ command failed: {e}")
            return {"status": "error", "message": str(e)}

    def run_command(self, command: str) -> None:
        """Run a command on the robot."""
        self.logger.log(f"Running command {command} on device number {self.device_number}.")

        # Example of sending a generic command via ZMQ
        zmq_command = {"action": "run_command", "command": command, "device_number": self.device_number}
        response = self.send_zmq_command(zmq_command)

        if response.get("status") != "success":
            self.logger.log(f"Command failed: {response.get('message', 'Unknown error')}")

    def move_to_location(self, location_coordinates: list, coordinate_type: Optional[CoordinateType] = None) -> bool:
        """Move robot to specified location coordinates."""
        self.logger.log(f"Moving to location: {location_coordinates}")

        # Use provided coordinate type or default
        coord_type = coordinate_type or self.coordinate_type

        try:
            # Convert location to joint angles
            joint_angles = self.process_location(location_coordinates, coord_type)

            # Validate joint angles
            if not validate_ur5e_joints(joint_angles):
                self.logger.log(f"Joint angles out of bounds: {joint_angles}")
                return False

            # Send move command via ZMQ
            zmq_command = {"action": "move_joints", "joint_angles": joint_angles}
            response = self.send_zmq_command(zmq_command)

            success = response.get("status") == "success"
            if success:
                self.logger.log(f"Successfully moved to location {location_coordinates}")
            else:
                self.logger.log(f"Failed to move to location: {response.get('message', 'Unknown error')}")

            return success

        except Exception as e:
            self.logger.log(f"Error processing location {location_coordinates}: {e}")
            return False

    def get_current_position(self) -> list:
        """Get current robot joint positions."""
        zmq_command = {"action": "get_joints"}
        response = self.send_zmq_command(zmq_command)

        if response.get("status") == "success":
            return response.get("joint_angles", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            self.logger.log(f"Failed to get position: {response.get('message', 'Unknown error')}")
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def process_location(self, location_coordinates: list, coordinate_type: CoordinateType) -> list:
        """Process location coordinates based on coordinate system type."""
        if not location_coordinates:
            return [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]  # Default home position

        if coordinate_type == CoordinateType.JOINT_ANGLES:
            return self.handle_joint_angles(location_coordinates)
        elif coordinate_type == CoordinateType.CARTESIAN:
            return self.handle_cartesian_coordinates(location_coordinates)
        else:
            raise ValueError(f"Unsupported coordinate type: {coordinate_type}")

    def handle_joint_angles(self, joint_angles: list) -> list:
        """Handle joint angle input."""
        if len(joint_angles) == 6:
            return list(joint_angles)
        elif len(joint_angles) == 4:
            # Legacy 4-DOF to 6-DOF conversion
            self.logger.log("Converting legacy 4-DOF to 6-DOF joint angles")
            return self.legacy_4dof_to_6dof(joint_angles)
        else:
            raise ValueError(f"Expected 6 joint angles, got {len(joint_angles)}")

    def handle_cartesian_coordinates(self, pose: list) -> list:
        """Handle Cartesian coordinate input (pose)."""
        if len(pose) == 6:
            # Full 6-DOF pose [x, y, z, rx, ry, rz]
            return simple_inverse_kinematics(pose)
        elif len(pose) == 3:
            # Position only [x, y, z] - assume zero orientation
            full_pose = pose + [0.0, 0.0, 0.0]
            return simple_inverse_kinematics(full_pose)
        elif len(pose) == 4:
            # Legacy format - convert to pose
            self.logger.log("Converting legacy 4-element coordinates to pose")
            return self.legacy_4dof_to_6dof(pose)
        else:
            raise ValueError(f"Expected 3 or 6 pose elements, got {len(pose)}")

    def legacy_4dof_to_6dof(self, coords: list) -> list:
        """Convert legacy 4-DOF coordinates to 6-DOF joint angles."""
        if len(coords) < 2:
            return [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]

        x, y = coords[0], coords[1]

        # Convert legacy coordinate system to joint angles
        # Normalize legacy coordinates (assumed to be in some arbitrary units)
        joint_1 = (x - 150) / 100.0  # Base rotation
        joint_2 = -1.57 + (y - 150) / 100.0  # Shoulder lift

        # Use additional coordinates if available
        joint_3 = coords[2] / 100.0 if len(coords) > 2 else 0.0
        joint_4 = coords[3] / 100.0 if len(coords) > 3 else -1.57

        return [joint_1, joint_2, joint_3, joint_4, 0.0, 0.0]

    def detect_coordinate_type(self, location_coordinates: list) -> CoordinateType:
        """Automatically detect coordinate system type based on values."""
        if len(location_coordinates) != 6:
            return self.coordinate_type  # Use default for non-6DOF inputs

        # Heuristic: joint angles are typically in radians (-π to π range)
        # Cartesian coordinates are typically in meters (larger values)
        max_abs_value = max(abs(x) for x in location_coordinates)

        if max_abs_value > 10:  # Likely Cartesian (meters or mm)
            return CoordinateType.CARTESIAN
        else:  # Likely joint angles (radians)
            return CoordinateType.JOINT_ANGLES

    def get_pose_from_joints(self) -> list:
        """Get current end-effector pose from joint positions."""
        joints = self.get_current_position()
        return get_pose_from_joint_angles(joints, "UR5e")


class SimUR5eNode(RestNode):
    """A robot node module with 6-DOF support."""

    sim_ur5e: SimUR5eInterface = None

    def set_robot_interface(self, robot_interface: SimUR5eInterface) -> None:
        """Set the robot interface instance."""
        self.sim_ur5e = robot_interface

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        if self.sim_ur5e is None:
            raise RuntimeError("Robot interface not set. Call set_robot_interface() before starting node.")

        resource_name = "sim_ur5e_gripper_" + str(self.node_definition.node_name)
        slot_def = SlotResourceDefinition(resource_name=resource_name)
        self.gripper = self.resource_client.init_resource(slot_def)
        self.logger.log("Robot initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        if self.sim_ur5e:
            del self.sim_ur5e

    def state_handler(self) -> dict[str, any]:
        """Periodically called to get the current state of the node."""
        if self.sim_ur5e is not None:
            current_position = self.sim_ur5e.get_current_position()
            self.node_state = {
                "sim_ur5e_status_code": self.sim_ur5e.status_code,
                "current_joint_positions": current_position,
            }

    def _exception_handler(self, e: Exception, set_node_errored: bool = True):
        """Overrides the default exception handler to force a shutdown."""
        super()._exception_handler(e, set_node_errored)
        self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
        os.kill(os.getpid(), signal.SIGTERM)

    @action
    def transfer(
        self,
        source: Annotated[LocationArgument, "The source location"],
        target: Annotated[LocationArgument, "the target location"],
        coordinate_type: Annotated[Optional[str], "Coordinate system: 'joint_angles' or 'cartesian'"] = None,
        auto_detect_coordinates: Annotated[bool, "Automatically detect coordinate system"] = False,
    ) -> ActionResult:
        """Transfer a plate from source to target location using ZMQ robot control."""

        # Determine coordinate system
        coord_type = None
        if coordinate_type:
            try:
                coord_type = CoordinateType(coordinate_type.lower())
            except ValueError:
                return ActionFailed(errors=[Error(message=f"Invalid coordinate type: {coordinate_type}")])

        if self.resource_client:
            try:
                popped_plate, _ = self.resource_client.pop(resource=source.resource_id)
            except Exception:
                return ActionFailed(errors=[Error(message="No plate in source!")])

            # Move to source location via ZMQ
            source_coords = source.location  # LocationArgument.location contains the coordinates

            # Auto-detect coordinate system if requested
            if auto_detect_coordinates and coord_type is None:
                coord_type = self.sim_ur5e.detect_coordinate_type(source_coords)
                self.logger.log(f"Auto-detected coordinate system: {coord_type.value}")

            if not self.sim_ur5e.move_to_location(source_coords, coord_type):
                return ActionFailed(errors=[Error(message="Failed to move to source location")])

            # Simulate gripper pickup
            self.resource_client.push(resource=self.gripper.resource_id, child=popped_plate)
            self.logger.log("Picked up plate from source")

            time.sleep(1)  # Simulate pick operation time

            # Move to target location via ZMQ
            target_coords = target.location  # LocationArgument.location contains the coordinates

            # Auto-detect for target as well if needed
            if auto_detect_coordinates and coord_type is None:
                coord_type = self.sim_ur5e.detect_coordinate_type(target_coords)

            if not self.sim_ur5e.move_to_location(target_coords, coord_type):
                return ActionFailed(errors=[Error(message="Failed to move to target location")])

            # Simulate gripper release
            popped_plate, _ = self.resource_client.pop(resource=self.gripper.resource_id)
            self.resource_client.push(resource=target.resource_id, child=popped_plate)
            self.logger.log("Placed plate at target")

            time.sleep(1)  # Simulate place operation time

        return ActionSucceeded()

    def get_location(self) -> AdminCommandResponse:
        """Get the robot's current location"""
        if self.sim_ur5e:
            position = self.sim_ur5e.get_current_position()
            return AdminCommandResponse(data=position)
        return AdminCommandResponse(data=[0, 0, 0, 0, 0, 0])

    @action
    def movej(
        self,
        joints: Annotated[Union[LocationArgument, list], "Joint angles to move to"],
        coordinate_type: Annotated[Optional[str], "Coordinate system override"] = None,
    ) -> ActionResult:
        """Move the robot using joint angles"""
        try:
            coord_type = CoordinateType(coordinate_type) if coordinate_type else CoordinateType.JOINT_ANGLES

            if isinstance(joints, LocationArgument):
                joint_coords = joints.location
            else:
                joint_coords = joints

            if self.sim_ur5e.move_to_location(joint_coords, coord_type):
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to move to joint position")])

        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Joint movement error: {str(e)}")])

    @action
    def movel(
        self,
        target: Annotated[Union[LocationArgument, list], "Cartesian target to move to"],
        coordinate_type: Annotated[Optional[str], "Coordinate system override"] = None,
    ) -> ActionResult:
        """Move the robot using linear motion"""
        try:
            coord_type = CoordinateType(coordinate_type) if coordinate_type else CoordinateType.CARTESIAN

            if isinstance(target, LocationArgument):
                target_coords = target.location
            else:
                target_coords = target

            if self.sim_ur5e.move_to_location(target_coords, coord_type):
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to move to target position")])

        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Linear movement error: {str(e)}")])

    @action
    def get_pose(
        self,
    ) -> ActionResult:
        """Get current end-effector pose"""
        try:
            if self.sim_ur5e:
                pose = self.sim_ur5e.get_pose_from_joints()
                return ActionSucceeded(data={"pose": pose})
            else:
                return ActionFailed(errors=[Error(message="Robot interface not available")])
        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Failed to get pose: {str(e)}")])


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start a MADSci robot node with ZMQ interface")
    parser.add_argument(
        "--zmq_server",
        default="tcp://localhost:5555",
        help="ZMQ server address (default: tcp://localhost:5555)"
    )
    parser.add_argument(
        "--device_number",
        type=int,
        default=0,
        help="Device number for the robot (default: 0)"
    )
    parser.add_argument(
        "--coordinate_type",
        default="joint_angles",
        choices=["joint_angles", "cartesian"],
        help="Default coordinate system (default: joint_angles)"
    )
    parser.add_argument(
        "--robot_model",
        default="UR5e",
        help="Robot model (default: UR5e)"
    )

    # Parse args, but also pass through any MADSci node args
    args, unknown_args = parser.parse_known_args()

    # Create robot interface with CLI-specified parameters
    print(f"Connecting to ZMQ server at: {args.zmq_server}")
    print(f"Coordinate system: {args.coordinate_type}")
    print(f"Robot model: {args.robot_model}")

    robot_interface = SimUR5eInterface(
        device_number=args.device_number,
        zmq_server_url=args.zmq_server,
        coordinate_type=CoordinateType(args.coordinate_type),
        robot_model=args.robot_model
    )

    # Create and configure the node
    node = SimUR5eNode()
    node.set_robot_interface(robot_interface)

    # Start the node (this will call startup_handler)
    node.start_node()
