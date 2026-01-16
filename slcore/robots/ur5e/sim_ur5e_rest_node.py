import os
import signal
from typing import Annotated, Optional, Union

from madsci.client.resource_client import ResourceClient
from madsci.common.types.action_types import ActionFailed, ActionSucceeded
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
from madsci.node_module.helpers import action
from ur_rest_node import URNode, URNodeConfig

from slcore.robots.common.types import CoordinateType
from slcore.robots.ur5e.sim_ur5e_interface import SimUR5e


class SimUR5eNodeConfig(URNodeConfig):
    """Configuration for the UR node module."""

    resource_server_url: str = "http://localhost:8013"
    "Temporary hack"

    ur_ip: str = ""
    "Not used in simulation; setting a default value"

    zmq_server_url: str = "tcp://localhost:5555"
    "For Isaac Sim communication"


class SimUR5eNode(URNode):
    """A Rest Node object to control UR robots"""

    ur5e_interface: SimUR5e = None
    config: SimUR5eNodeConfig = SimUR5eNodeConfig()
    config_model = SimUR5eNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        try:
            # Setup resource client (following URNode pattern)
            if self.config.resource_server_url:
                self.resource_client = ResourceClient(self.config.resource_server_url)
                self.resource_owner = OwnershipInfo(node_id=self.node_definition.node_id)
            else:
                self.resource_client = None

            self.logger.log("Simulated UR5e node initializing...")

            # Create simulation interface instead of real UR interface
            self.ur5e_interface = SimUR5e(
                zmq_server_url=self.config.zmq_server_url,
                robot_model=self.config.ur_model
            )

            # Set up tool resource (like URNode does)
            self.tool_resource = None

            # Set up gripper resource for transfer operations
            if self.resource_client:
                self.gripper = self.resource_client.init_resource(
                    SlotResourceDefinition(
                        resource_name="ur_gripper_" + str(self.node_definition.node_name),
                        owner=self.resource_owner,
                    )
                )
            else:
                self.gripper = None

        except Exception as err:
            self.logger.log_error(f"Error starting the simulated UR5e Node: {err}")
            self.startup_has_run = False
        else:
            self.startup_has_run = True
            self.logger.log("Simulated UR5e node initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        try:
            self.logger.log("Shutting down simulated UR5e node")
            if self.ur5e_interface:
                del self.ur5e_interface
                self.ur5e_interface = None
            self.shutdown_has_run = True
            self.logger.log("Simulated UR5e node shutdown complete.")
        except Exception as err:
            self.logger.log_error(f"Error shutting down the simulated UR5e Node: {err}")

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        try:
            if self.ur5e_interface is not None:
                current_position = self.ur5e_interface.getj()
                self.node_state = {
                    "ur_status_code": "READY",  # Match URNode state format
                    "current_joint_angles": current_position,
                    "simulation_mode": True,
                    "zmq_server_url": self.config.zmq_server_url,
                }
        except Exception as err:
            self.logger.log_error(f"Error updating UR5e node state: {err}")

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="getj", description="Get joint angles")
    def getj(self):
        """Get joint positions"""
        try:
            joints = self.ur5e_interface.getj()
            self.logger.log_info(joints)
            return ActionSucceeded(data={"joints": joints})
        except Exception as e:
            return ActionFailed(errors=f"Failed to get joint angles: {e}")

    @action(name="set_freedrive", description="Free robot joints")
    def set_freedrive(self, timeout: Annotated[int, "how long to do freedrive"] = 60):
        """Set the robot into freedrive"""
        try:
            success = self.ur5e_interface.set_freedrive(timeout)
            return ActionSucceeded() if success else ActionFailed(errors="Failed to enable freedrive")
        except Exception as e:
            return ActionFailed(errors=f"Error in set_freedrive: {e}")

    @action(name="set_movement_params", description="Set speed and acceleration parameters")
    def set_movement_params(
        self,
        tcp_pose: Optional[list] = None,
        velocity: Optional[float] = None,
        acceleration: Optional[float] = None,
        gripper_speed: Optional[float] = None,
        gripper_force: Optional[float] = None,
    ):
        """Configure the robot's movement parameters for subsequent transfers"""
        # For simulation, just log the parameters (could extend ZMQ interface later)
        if tcp_pose is not None:
            self.logger.log(f"TCP pose set to: {tcp_pose}")
        if velocity is not None:
            self.logger.log(f"Velocity set to: {velocity}")
        if acceleration is not None:
            self.logger.log(f"Acceleration set to: {acceleration}")
        if gripper_speed is not None:
            self.logger.log(f"Gripper speed set to: {gripper_speed}")
        if gripper_force is not None:
            self.logger.log(f"Gripper force set to: {gripper_force}")
        return ActionSucceeded()

    @action
    def movej(
        self,
        joints: Annotated[Union[LocationArgument, list], "Joint angles to move to"],
    ):
        """Move the robot using joint angles"""
        try:
            if isinstance(joints, LocationArgument):
                joint_angles = joints.location
            else:
                joint_angles = joints

            if self.ur5e_interface.move_to_location(joint_angles):
                return ActionSucceeded()
            else:
                return ActionFailed(errors="Failed to move to joint position")

        except Exception as e:
            return ActionFailed(errors=f"Joint movement error: {e}")

    @action(name="toggle_gripper", description="Move the robot gripper")
    def toggle_gripper(
        self,
        open: Annotated[bool, "Open?"] = False,
        close: Annotated[bool, "Close?"] = False,
    ):
        """Open or close the robot gripper."""
        try:
            if open:
                success = self.ur5e_interface.open_gripper()
                self.logger.log("Gripper opened")
            elif close:
                success = self.ur5e_interface.close_gripper()
                self.logger.log("Gripper closed")
            else:
                self.logger.log("No action taken")
                return ActionSucceeded()

            return ActionSucceeded() if success else ActionFailed(errors="Gripper operation failed")
        except Exception as err:
            self.logger.log_error(err)
            return ActionFailed(errors=str(err))

    @action(
        name="gripper_transfer",
        description="Execute a transfer between source and target locations using Robotiq grippers",
    )
    def gripper_transfer(
        self,
        home: Annotated[Union[LocationArgument, list], "Home location"],
        source: Annotated[Union[LocationArgument, list], "Location to transfer sample from"],
        target: Annotated[Union[LocationArgument, list], "Location to transfer sample to"],
        source_approach_axis: Annotated[Optional[str], "Source location approach axis, (X/Y/Z)"] = "z",
        target_approach_axis: Annotated[Optional[str], "Source location approach axis, (X/Y/Z)"] = "z",
        source_approach_distance: Annotated[Optional[float], "Approach distance in meters"] = 0.05,
        target_approach_distance: Annotated[Optional[float], "Approach distance in meters"] = 0.05,
        gripper_open: Annotated[Optional[int], "Set a max value for the gripper open state"] = 0,
        gripper_close: Annotated[Optional[int], "Set a min value for the gripper close state"] = 255,
        joint_angle_locations: Annotated[bool, "Use joint angles for all the locations"] = True,
    ):
        """Make a transfer using the finger gripper."""
        try:
            # Check if required locations are provided
            if not source or not target or not home:
                return ActionFailed(errors="Source, target and home locations must be provided")

            if self.resource_client:
                # Set up tool resource if not already done
                if not self.tool_resource:
                    self.tool_resource = self.resource_client.init_resource(
                        SlotResourceDefinition(
                            resource_name="ur_gripper",
                            owner=self.resource_owner,
                        )
                    )

            # For now, implement using existing transfer() method
            # TODO: Extend to use approach distances and gripper parameters
            return self.transfer(source, target)
        except Exception as e:
            return ActionFailed(errors=f"Error in gripper_transfer: {e}")

    @action()
    def gripper_pick(
        self,
        home: Annotated[Union[LocationArgument, list], "Home location"],
        source: Annotated[Union[LocationArgument, list], "Location to transfer sample from"],
        source_approach_axis: Annotated[Optional[str], "Source location approach axis, (X/Y/Z)"] = "z",
        source_approach_distance: Annotated[Optional[float], "Approach distance in meters"] = 0.05,
        gripper_close: Annotated[Optional[int], "Set a min value for the gripper close state"] = 255,
        joint_angle_locations: Annotated[bool, "Use joint angles for all the locations"] = True,
    ):
        """Use the gripper to pick a piece of labware from the specified source"""
        if self.resource_client:
            # Set up tool resource if not already done
            if not self.tool_resource:
                self.tool_resource = self.resource_client.init_resource(
                    SlotResourceDefinition(
                        resource_name="ur_gripper",
                        owner=self.resource_owner,
                    )
                )

        # For simulation, just move to source and close gripper
        try:
            # Note: CoordinateType is available but not yet used by the interface
            # For now, joint_angle_locations=True (default) means we expect joint angles
            if not joint_angle_locations:
                return ActionFailed(errors="Cartesian coordinates not yet supported in simulation")

            if isinstance(source, LocationArgument):
                source_coords = source.location
            else:
                source_coords = source

            if self.ur5e_interface.move_to_location(source_coords):
                success = self.ur5e_interface.close_gripper()
                return ActionSucceeded() if success else ActionFailed(errors="Failed to close gripper")
            else:
                return ActionFailed(errors="Failed to move to source location")
        except Exception as e:
            return ActionFailed(errors=f"Gripper pick error: {e}")

    def get_location(self) -> AdminCommandResponse:
        """Get the robot's current location"""
        if self.ur5e_interface:
            position = self.ur5e_interface.getj()
            return AdminCommandResponse(data=position)
        return AdminCommandResponse(data=[0, 0, 0, 0, 0, 0]) # TODO: Vibe code residue


if __name__ == "__main__":
    # Use standard MADSci node initialization
    node = SimUR5eNode()
    node.start_node()
