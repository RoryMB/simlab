import os
import signal
from typing import Annotated, Optional

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from sim_thermocycler_interface import SimThermocycler


class SimThermocyclerNodeConfig(RestNodeConfig):
    """Configuration for the thermocycler node module."""

    zmq_server_url: str = "tcp://localhost:5560"


class SimThermocyclerNode(RestNode):
    """A Rest Node object to control Thermocycler devices"""

    thermocycler_interface: SimThermocycler = None
    config: SimThermocyclerNodeConfig = SimThermocyclerNodeConfig()
    config_model = SimThermocyclerNodeConfig

    def startup_handler(self) -> None:
        """Initialize the node."""
        self.thermocycler_interface = SimThermocycler(
            zmq_server_url=self.config.zmq_server_url,
        )
        self.thermocycler_interface.initialize_device()

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.thermocycler_interface is not None:
            self.node_state = {
                "thermocycler_status_code": self.thermocycler_interface.status_code,
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            }

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="open", description="Open thermocycler lid")
    def open(self) -> ActionResult:
        """Open thermocycler lid."""
        success = self.thermocycler_interface.open()
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Failed to open thermocycler lid"]
            )

    @action(name="close", description="Close thermocycler lid")
    def close(self) -> ActionResult:
        """Close thermocycler lid."""
        success = self.thermocycler_interface.close()
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Failed to close thermocycler lid"]
            )

    @action(name="run_program", description="Run a thermocycling program")
    def run_program(
        self,
        program_number: Annotated[int, "Program number to run"],
    ) -> ActionResult:
        """Run a thermocycling program."""
        success = self.thermocycler_interface.run_program(program_number)
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Failed to run thermocycler program"]
            )


if __name__ == "__main__":
    thermocycler_node = SimThermocyclerNode()
    thermocycler_node.start_node()