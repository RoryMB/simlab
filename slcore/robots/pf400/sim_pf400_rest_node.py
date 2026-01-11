import os
import signal
from typing import Annotated, Optional

from madsci.client.resource_client import ResourceClient
from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.resource_types import Slot
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.resource_types.definitions import SlotResourceDefinition
from madsci.node_module.helpers import action
from pf400_rest_node import PF400Node, PF400NodeConfig

from slcore.robots.pf400.sim_pf400_interface import SimPF400


class SimPF400NodeConfig(PF400NodeConfig):
    """Configuration for the pf400 node module."""

    pf400_ip: Optional[str] = ""
    "Not used in simulation; setting a default value"

    zmq_server_url: str = "tcp://localhost:5557"
    "For Isaac Sim communication"

    resource_server_url: str = "http://localhost:8013"
    "Resource server URL for MADSci resource management"


class SimPF400Node(PF400Node):
    """A Rest Node object to control PF400 robots"""

    pf400_interface: SimPF400 = None
    config: SimPF400NodeConfig = SimPF400NodeConfig()
    config_model = SimPF400NodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""

        # Setup resource client with defensive null check (following UR5e pattern)
        if hasattr(self.config, 'resource_server_url') and self.config.resource_server_url:
            self.resource_client = ResourceClient(self.config.resource_server_url)
            self.resource_owner = OwnershipInfo(node_id=self.node_definition.node_id)
        else:
            self.resource_client = None

        gripper_resource_id = None

        # Only setup resource templates if resource_client is available
        if self.resource_client:
            gripper_slot = Slot(
                resource_name="pf400_gripper",
                resource_class="PF400Gripper",
                capacity=1,
                attributes={
                    "gripper_type": "finger",
                    "payload_kg": 0.5,
                    "payload_lb": 1.1,
                    "max_grip_force_newton": 23.0,
                    "grip_width_range": [80.0, 140.0],
                    "description": "PF400 robot gripper slot",
                },
            )

            self.resource_client.init_template(
                resource=gripper_slot,
                template_name="pf400_gripper",
                description="Template for PF400 robot gripper slot. Used to track what the robot is currently holding.",
                required_overrides=["resource_name"],
                tags=["pf400", "gripper", "slot"],
                created_by=self.node_definition.node_id,
                version="1.0.0",
            )

            self.gripper_resource = self.resource_client.create_resource_from_template(
                template_name="pf400_gripper",
                resource_name=f"{self.node_definition.node_name}.gripper",
                add_to_database=True,
            )
            gripper_resource_id = self.gripper_resource.resource_id

        self.pf400_interface = SimPF400(
            zmq_server_url=self.config.zmq_server_url,
            resource_client=self.resource_client,
            gripper_resource_id=gripper_resource_id,
        )
        self.pf400_interface.initialize_robot()

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.pf400_interface is not None:
            status = self.pf400_interface.get_status()
            self.node_state = {
                "pf400_status_code": self.pf400_interface.status_code,
                "current_joint_angles": status["joint_angles"],
                "gripper_state": status["gripper_state"],
                "is_moving": status["is_moving"],
                "collision_detected": status["collision_detected"],
                "motion_complete": status["motion_complete"],
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            }

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="transfer", description="Transfer a plate from one location to another")
    def transfer(
        self,
        source: Annotated[LocationArgument, "Location to pick a plate from"],
        target: Annotated[LocationArgument, "Location to place a plate to"],
        source_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
        target_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
        source_plate_rotation: Annotated[str, "Orientation of the plate at the source, wide or narrow"] = "",
        target_plate_rotation: Annotated[str, "Final orientation of the plate at the target, wide or narrow"] = "",
    ) -> ActionResult:
        return super().transfer(source, target, source_approach, target_approach, source_plate_rotation, target_plate_rotation)

    @action(name="pick_plate", description="Pick a plate from a source location")
    def pick_plate(
        self,
        source: Annotated[LocationArgument, "Location to pick a plate from"],
        source_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
    ) -> ActionResult:
        """Picks a plate from `source`, optionally moving first to `source_approach`."""
        return super().pick_plate(source, source_approach)

    @action(name="place_plate", description="Place a plate in a target location, optionally moving first to target_approach")
    def place_plate(
        self,
        target: Annotated[LocationArgument, "Location to place a plate to"],
        target_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
    ) -> ActionResult:
        """Place a plate in the `target` location, optionally moving first to `target_approach`."""
        return super().place_plate(target, target_approach)

    @action(name="remove_lid", description="Remove a lid from a plate")
    def remove_lid(
        self,
        source: Annotated[LocationArgument, "Location to pick a plate from"],
        target: Annotated[LocationArgument, "Location to place a plate to"],
        source_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
        target_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
        source_plate_rotation: Annotated[str, "Orientation of the plate at the source, wide or narrow"] = "",
        target_plate_rotation: Annotated[str, "Final orientation of the plate at the target, wide or narrow"] = "",
        lid_height: Annotated[float, "height of the lid, in steps"] = 7.0,
    ) -> ActionResult:
        """Remove a lid from a plate located at location ."""
        return super().remove_lid(source, target, source_approach, target_approach, source_plate_rotation, target_plate_rotation, lid_height)

    @action(name="replace_lid", description="Replace a lid on a plate")
    def replace_lid(
        self,
        source: Annotated[LocationArgument, "Location to pick a plate from"],
        target: Annotated[LocationArgument, "Location to place a plate to"],
        source_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
        target_approach: Annotated[Optional[LocationArgument], "Location to approach from"] = None,
        source_plate_rotation: Annotated[str, "Orientation of the plate at the source, wide or narrow"] = "",
        target_plate_rotation: Annotated[str, "Final orientation of the plate at the target, wide or narrow"] = "",
        lid_height: Annotated[float, "height of the lid, in steps"] = 7.0,
    ) -> ActionResult:
        """Replace a lid on a plate."""
        return super().replace_lid(source, target, source_approach, target_approach, source_plate_rotation, target_plate_rotation, lid_height)


if __name__ == "__main__":
    pf400_node = SimPF400Node()
    pf400_node.start_node()
