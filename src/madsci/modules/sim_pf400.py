"""A PF400 robot module with ZMQ client interface for Isaac Sim integration."""

import argparse
import json
import os
import signal
import sys
import time
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


class SimPF400Interface:
    """A PF400 robot interface that communicates via ZMQ with Isaac Sim."""

    status_code: int = 0
    device_number: int = 0

    def __init__(
        self,
        device_number: int = 0,
        zmq_server_url: str = "tcp://localhost:5557",
        logger: Optional[EventClient] = None,
    ) -> "SimPF400Interface":
        """Initialize the PF400 ZMQ client."""
        self.logger = logger or EventClient()
        self.device_number = device_number
        self.zmq_server_url = zmq_server_url

        # Initialize ZMQ client
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.zmq_server_url)

        self.logger.log(f"SimPF400Interface connected to ZMQ server at {self.zmq_server_url}")

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

    def move_to_position(self, joint_angles: list) -> bool:
        """Move PF400 to specified joint positions."""
        self.logger.log(f"Moving to joint positions: {joint_angles}")

        if len(joint_angles) != 6:
            self.logger.log(f"Expected 6 joint angles, got {len(joint_angles)}")
            return False

        try:
            # Send move command via ZMQ
            zmq_command = {"action": "move_joints", "joint_angles": joint_angles}
            response = self.send_zmq_command(zmq_command)

            success = response.get("status") == "success"
            if success:
                self.logger.log(f"Successfully moved to position {joint_angles}")
            else:
                self.logger.log(f"Failed to move to position: {response.get('message', 'Unknown error')}")

            return success

        except Exception as e:
            self.logger.log(f"Error moving to position {joint_angles}: {e}")
            return False

    def move_to_cartesian(self, cartesian_coords: list) -> bool:
        """Move PF400 to specified cartesian coordinates."""
        self.logger.log(f"Moving to cartesian position: {cartesian_coords}")

        try:
            # Send cartesian move command via ZMQ
            zmq_command = {"action": "move_cartesian", "cartesian_coordinates": cartesian_coords}
            response = self.send_zmq_command(zmq_command)

            success = response.get("status") == "success"
            if success:
                self.logger.log(f"Successfully moved to cartesian position {cartesian_coords}")
            else:
                self.logger.log(f"Failed to move to cartesian position: {response.get('message', 'Unknown error')}")

            return success

        except Exception as e:
            self.logger.log(f"Error moving to cartesian position {cartesian_coords}: {e}")
            return False

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
            return {
                "joint_angles": response.get("joint_angles", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                "gripper_state": response.get("gripper_state", "unknown"),
                "is_homed": response.get("is_homed", False)
            }
        else:
            self.logger.log(f"Failed to get status: {response.get('message', 'Unknown error')}")
            return {
                "joint_angles": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "gripper_state": "unknown",
                "is_homed": False
            }


class SimPF400Node(RestNode):
    """A PF400 robot node module for Isaac Sim integration."""

    sim_pf400: SimPF400Interface = None

    def set_robot_interface(self, robot_interface: SimPF400Interface) -> None:
        """Set the robot interface instance."""
        self.sim_pf400 = robot_interface

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        if self.sim_pf400 is None:
            raise RuntimeError("Robot interface not set. Call set_robot_interface() before starting node.")

        resource_name = "sim_pf400_gripper_" + str(self.node_definition.node_name)
        slot_def = SlotResourceDefinition(resource_name=resource_name)
        self.gripper = self.resource_client.init_resource(slot_def)
        self.logger.log("PF400 Robot initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        if self.sim_pf400:
            del self.sim_pf400

    def state_handler(self) -> dict[str, any]:
        """Periodically called to get the current state of the node."""
        if self.sim_pf400 is not None:
            status = self.sim_pf400.get_status()
            self.node_state = {
                "sim_pf400_status_code": self.sim_pf400.status_code,
                "current_joint_positions": status["joint_angles"],
                "gripper_state": status["gripper_state"],
                "is_homed": status["is_homed"]
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
    ) -> ActionResult:
        """Transfer a plate from source to target location using ZMQ robot control."""

        if self.resource_client:
            try:
                popped_plate, _ = self.resource_client.pop(resource=source.resource_id)
            except Exception:
                return ActionFailed(errors=[Error(message="No plate in source!")])

            # Move to source location via ZMQ
            source_coords = source.location  # LocationArgument.location contains the coordinates

            if not self.sim_pf400.move_to_position(source_coords):
                return ActionFailed(errors=[Error(message="Failed to move to source location")])

            # Open gripper and simulate pickup
            if not self.sim_pf400.open_gripper():
                return ActionFailed(errors=[Error(message="Failed to open gripper")])
                
            self.resource_client.push(resource=self.gripper.resource_id, child=popped_plate)
            self.logger.log("Picked up plate from source")

            # Close gripper
            if not self.sim_pf400.close_gripper():
                return ActionFailed(errors=[Error(message="Failed to close gripper")])

            time.sleep(1)  # Simulate pick operation time

            # Move to target location via ZMQ
            target_coords = target.location  # LocationArgument.location contains the coordinates

            if not self.sim_pf400.move_to_position(target_coords):
                return ActionFailed(errors=[Error(message="Failed to move to target location")])

            # Open gripper and simulate release
            if not self.sim_pf400.open_gripper():
                return ActionFailed(errors=[Error(message="Failed to open gripper for release")])
                
            popped_plate, _ = self.resource_client.pop(resource=self.gripper.resource_id)
            self.resource_client.push(resource=target.resource_id, child=popped_plate)
            self.logger.log("Placed plate at target")

            time.sleep(1)  # Simulate place operation time

        return ActionSucceeded()

    def get_location(self) -> AdminCommandResponse:
        """Get the robot's current location"""
        if self.sim_pf400:
            position = self.sim_pf400.get_current_position()
            return AdminCommandResponse(data=position)
        return AdminCommandResponse(data=[0, 0, 0, 0, 0, 0])

    @action
    def movej(
        self,
        joints: Annotated[Union[LocationArgument, list], "Joint angles to move to"],
    ) -> ActionResult:
        """Move the robot using joint angles"""
        try:
            if isinstance(joints, LocationArgument):
                joint_coords = joints.location
            else:
                joint_coords = joints

            if self.sim_pf400.move_to_position(joint_coords):
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to move to joint position")])

        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Joint movement error: {str(e)}")])

    @action
    def move_cartesian(
        self,
        target: Annotated[Union[LocationArgument, list], "Cartesian target to move to"],
    ) -> ActionResult:
        """Move the robot using cartesian coordinates"""
        try:
            if isinstance(target, LocationArgument):
                target_coords = target.location
            else:
                target_coords = target

            if self.sim_pf400.move_to_cartesian(target_coords):
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to move to cartesian position")])

        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Cartesian movement error: {str(e)}")])

    @action
    def home(
        self,
    ) -> ActionResult:
        """Move robot to home position"""
        try:
            if self.sim_pf400.home_robot():
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to home robot")])
        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Failed to home robot: {str(e)}")])

    @action
    def gripper_open(
        self,
    ) -> ActionResult:
        """Open robot gripper"""
        try:
            if self.sim_pf400.open_gripper():
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to open gripper")])
        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Failed to open gripper: {str(e)}")])

    @action
    def gripper_close(
        self,
    ) -> ActionResult:
        """Close robot gripper"""
        try:
            if self.sim_pf400.close_gripper():
                return ActionSucceeded()
            else:
                return ActionFailed(errors=[Error(message="Failed to close gripper")])
        except Exception as e:
            return ActionFailed(errors=[Error(message=f"Failed to close gripper: {str(e)}")])


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start a MADSci PF400 node with ZMQ interface")
    parser.add_argument(
        "--zmq_server",
        default="tcp://localhost:5557",
        help="ZMQ server address (default: tcp://localhost:5557)"
    )
    parser.add_argument(
        "--device_number",
        type=int,
        default=0,
        help="Device number for the robot (default: 0)"
    )

    # Parse args, but also pass through any MADSci node args
    args, unknown_args = parser.parse_known_args()

    # Create robot interface with CLI-specified parameters
    print(f"Connecting to ZMQ server at: {args.zmq_server}")
    print(f"Device number: {args.device_number}")

    robot_interface = SimPF400Interface(
        device_number=args.device_number,
        zmq_server_url=args.zmq_server,
    )

    # Create and configure the node
    node = SimPF400Node()
    node.set_robot_interface(robot_interface)

    # Start the node (this will call startup_handler)
    node.start_node()