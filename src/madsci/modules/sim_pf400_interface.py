import json
import time
from typing import Optional

import zmq

from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.location_types import LocationArgument


class SimPF400:
    """Main Driver Class for the PF400 Robot Arm."""

    status_code: int = 0

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5557",
        resource_client: ResourceClient = None,
        gripper_resource_id: Optional[str] = None,
        logger: Optional[EventClient] = None,
    ) -> "SimPF400":
        """Initialize the PF400 ZMQ client."""
        self.logger = logger or EventClient()
        self.zmq_server_url = zmq_server_url
        self.resource_client = resource_client
        self.gripper_resource_id = gripper_resource_id

        # Initialize ZMQ client
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.zmq_server_url)

        self.logger.log(f"SimPF400 connected to ZMQ server at {self.zmq_server_url}")

    def __del__(self):
        """Clean up ZMQ resources."""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()

    def disconnect(self) -> None:
        pass

    def send_zmq_command(self, command: dict) -> dict:
        """Send a command via ZMQ and return the response."""
        try:
            # Send command
            self.socket.send_string(json.dumps(command))

            # Receive response with timeout
            if self.socket.poll(5000):  # 5 second timeout
                response_str = self.socket.recv_string()
                response = json.loads(response_str)
                return response
            else:
                return {"status": "error", "message": "Timeout waiting for response"}
        except Exception as e:
            self.logger.log(f"ZMQ command failed: {e}")
            return {"status": "error", "message": str(e)}

    def move_to_location_coordinates(self, location_coordinates: list) -> bool:
        """Move PF400 to location using joint angles from workcell definition."""
        self.logger.log(f"Moving to location coordinates: {location_coordinates}")

        if len(location_coordinates) != 7:
            self.logger.log(f"Expected 7 joint angles for PF400, got {len(location_coordinates)}")
            return False

        try:
            # Send move_joints command via ZMQ
            zmq_command = {
                "action": "move_joints",
                "joint_angles": location_coordinates
            }
            response = self.send_zmq_command(zmq_command)

            success = response.get("status") == "success"
            if success:
                self.logger.log(f"Successfully moved to joint angles {location_coordinates}")
                # Wait for motion to complete
                return self.wait_for_motion_complete()
            else:
                self.logger.log(f"Failed to move to joint angles: {response.get('message', 'Unknown error')}")

            return success

        except Exception as e:
            self.logger.log(f"Error moving to joint angles {location_coordinates}: {e}")
            return False

    def wait_for_motion_complete(self, max_wait: float = 30.0) -> bool:
        """Wait for robot motion to complete."""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = self.get_status()

            if status.get("collision_detected", False):
                self.logger.log("Motion stopped due to collision")
                return False

            if status.get("motion_complete", False) or not status.get("is_moving", False):
                self.logger.log("Motion completed successfully")
                return True

            time.sleep(0.1)

        self.logger.log(f"Motion did not complete within {max_wait} seconds")
        return False

    def move_to_approach_location(self, approach_coordinates) -> bool:
        """Move to approach location before main operation."""
        self.logger.log(f"Moving to approach location: {approach_coordinates}")

        # Extract coordinates from dictionary if needed
        if isinstance(approach_coordinates, dict):
            coords = approach_coordinates.get('location', [])
        else:
            coords = approach_coordinates

        # Use same coordinate handling as main location movement
        return self.move_to_location_coordinates(coords)

    def get_current_position(self) -> list:
        """Get current PF400 joint positions."""
        zmq_command = {"action": "get_joints"}
        response = self.send_zmq_command(zmq_command)

        if response.get("status") == "success":
            return response.get("joint_angles", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            self.logger.log(f"Failed to get position: {response.get('message', 'Unknown error')}")
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def home_robot(self) -> bool:
        """Move PF400 to home position."""
        self.logger.log("Homing PF400 robot")

        zmq_command = {"action": "home"}
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log("Successfully homed robot")
        else:
            self.logger.log(f"Failed to home robot: {response.get('message', 'Unknown error')}")

        return success

    def open_gripper(self) -> bool:
        """Open PF400 gripper."""
        self.logger.log("Opening PF400 gripper")

        zmq_command = {"action": "gripper_open"}
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log("Successfully opened gripper")
        else:
            self.logger.log(f"Failed to open gripper: {response.get('message', 'Unknown error')}")

        return success

    def close_gripper(self) -> bool:
        """Close PF400 gripper."""
        self.logger.log("Closing PF400 gripper")

        zmq_command = {"action": "gripper_close"}
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log("Successfully closed gripper")
        else:
            self.logger.log(f"Failed to close gripper: {response.get('message', 'Unknown error')}")

        return success

    def get_status(self) -> dict:
        """Get PF400 robot status."""
        zmq_command = {"action": "get_status"}
        response = self.send_zmq_command(zmq_command)

        if response.get("status") == "success":
            data = response.get("data", {})
            return {
                "joint_angles": data.get("joint_positions", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                "gripper_state": data.get("gripper_state", "unknown"),
                "is_moving": data.get("is_moving", False),
                "collision_detected": data.get("collision_detected", False),
                "motion_complete": data.get("motion_complete", True)
            }
        else:
            self.logger.log(f"Failed to get status: {response.get('message', 'Unknown error')}")
            return {
                "joint_angles": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "gripper_state": "unknown",
                "is_moving": False,
                "collision_detected": False,
                "motion_complete": True
            }

    def _get_hover_coords(self, coords: list, hover_height: float = 0.1) -> list:
        """Helper to create coordinates directly above a location."""
        # Create a copy so we don't modify the original list object
        hover_coords = list(coords)
        # Index 1 is the vertical axis
        # Set it to a safe height (e.g. 0.5 or current + offset)
        hover_coords[1] = hover_coords[1] + hover_height
        return hover_coords

    def pick_plate(
        self,
        source: LocationArgument,
        source_approach: LocationArgument = None,
        grab_offset: Optional[float] = None,
        approach_height_offset: Optional[float] = None,
        grip_width: Optional[int] = None,
    ) -> bool:
        """Pick a plate from a source location."""
        # Handle source approach if specified
        if source_approach:
            self.logger.log("Moving to source approach location")
            if not self.move_to_approach_location(source_approach.location if hasattr(source_approach, 'location') else source_approach):
                raise RuntimeError("Failed to move to source approach location")

        # [HACK] Move ABOVE Source (Approach safely)
        hover_source = self._get_hover_coords(source.location)
        self.logger.log("Moving to hover position above source")
        if not self.move_to_location_coordinates(hover_source):
            raise RuntimeError("Failed to hover above source")

        # Move to source location
        if not self.move_to_location_coordinates(source.location):
            raise RuntimeError("Failed to move to source location")

        # Close gripper to pick up plate
        if not self.close_gripper():
            raise RuntimeError("Failed to close gripper")

        # Update resource manager - plate picked from source
        if self.resource_client:
            popped_plate, updated_resource = self.resource_client.pop(resource=source.resource_id)
            self.resource_client.push(resource=self.gripper_resource_id, child=popped_plate)

        # [HACK] Move ABOVE Source (Retract safely)
        hover_source = self._get_hover_coords(source.location)
        self.logger.log("Retracting to hover position above source")
        if not self.move_to_location_coordinates(hover_source):
            raise RuntimeError("Failed to retract above source")

        self.logger.log("Picked up plate from source")
        return True

    def place_plate(
        self,
        target: LocationArgument,
        target_approach: LocationArgument = None,
        grab_offset: Optional[float] = None,
        approach_height_offset: Optional[float] = None,
        open_width: Optional[int] = None,
    ) -> bool:
        """Place a plate to a target location."""
        # Handle target approach if specified
        if target_approach:
            self.logger.log("Moving to target approach location")
            if not self.move_to_approach_location(target_approach.location if hasattr(target_approach, 'location') else target_approach):
                raise RuntimeError("Failed to move to target approach location")

        # [HACK] Move ABOVE Target (Approach safely)
        hover_target = self._get_hover_coords(target.location)
        self.logger.log("Moving to hover position above target")
        if not self.move_to_location_coordinates(hover_target):
            raise RuntimeError("Failed to hover above target")

        # [HACK] Move to slightly above target location
        hover_target = self._get_hover_coords(target.location, hover_height=0.02)
        if not self.move_to_location_coordinates(hover_target):
            raise RuntimeError("Failed to move to target location")

        # Open gripper to release plate
        if not self.open_gripper():
            raise RuntimeError("Failed to open gripper for release")

        # Update resource manager - plate placed at target
        if self.resource_client:
            popped_plate, updated_resource = self.resource_client.pop(resource=self.gripper_resource_id)
            self.resource_client.push(resource=target.resource_id, child=popped_plate)

        # [HACK] Move ABOVE Target (Retract safely)
        hover_target = self._get_hover_coords(target.location)
        self.logger.log("Retracting to hover position above target")
        if not self.move_to_location_coordinates(hover_target):
            raise RuntimeError("Failed to retract above target")

        self.logger.log("Placed plate at target")
        return True

    def transfer(
        self,
        source: LocationArgument,
        target: LocationArgument,
        source_approach: Optional[LocationArgument] = None,
        target_approach: Optional[LocationArgument] = None,
        source_plate_rotation: str = "",
        target_plate_rotation: str = "",
        rotation_deck: Optional[LocationArgument] = None,
        grab_offset: Optional[float] = None,
        source_approach_height_offset: Optional[float] = None,
        target_approach_height_offset: Optional[float] = None,
    ) -> bool:
        """Transfer a plate from source to target location using ZMQ robot control."""
        self.logger.log(f"Transfer from {source.location} to {target.location}")

        self.pick_plate(
            source=source,
            source_approach=source_approach,
        )

        self.place_plate(
            target=target,
            target_approach=target_approach,
        )

        return True

    def remove_lid(
        self,
        source: LocationArgument,
        target: LocationArgument,
        lid_height: float = 7.0,
        source_approach: Optional[LocationArgument] = None,
        target_approach: Optional[LocationArgument] = None,
        source_plate_rotation: str = "",
        target_plate_rotation: str = "",
    ) -> None:
        """Remove a lid from a plate."""
        self.logger.log(f"Removing lid with height {lid_height} steps")

        # For now, treat lid removal like a transfer operation
        # Real implementation would handle lid-specific gripping and height
        self.transfer(
            source=source,
            target=target,
            source_approach=source_approach,
            target_approach=target_approach,
            source_plate_rotation=source_plate_rotation,
            target_plate_rotation=target_plate_rotation
        )

    def replace_lid(
        self,
        source: LocationArgument,
        target: LocationArgument,
        lid_height: float = 7.0,
        source_approach: Optional[LocationArgument] = None,
        target_approach: Optional[LocationArgument] = None,
        source_plate_rotation: str = "",
        target_plate_rotation: str = "",
    ) -> None:
        """Replace a lid on a plate."""
        self.logger.log(f"Replacing lid with height {lid_height} steps")

        # For now, treat lid replacement like a transfer operation
        # Real implementation would handle lid-specific placement and height
        self.transfer(
            source=source,
            target=target,
            source_approach=source_approach,
            target_approach=target_approach,
            source_plate_rotation=source_plate_rotation,
            target_plate_rotation=target_plate_rotation
        )

    def get_joint_states(self) -> list:
        """Get current joint states (alias for get_current_position)."""
        return self.get_current_position()

    @property
    def movement_state(self) -> int:
        """Get movement state (1=READY, 2=BUSY) like PF400."""
        status = self.get_status()
        return 2 if status.get("is_moving", False) else 1

    def initialize_robot(self) -> None:
        """Initialize the robot (simulation doesn't need this but provides for API compatibility)."""
        self.logger.log("Simulation robot initialized")
