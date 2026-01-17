import os
import signal
from typing import Annotated

from madsci.common.types.action_types import ActionFailed
from madsci.node_module.helpers import action

from slcore.robots.common.simple_device_node import SimpleDeviceNodeConfig, SimpleDeviceRestNode
from slcore.robots.thermocycler.sim_thermocycler_interface import SimThermocycler


class SimThermocyclerNodeConfig(SimpleDeviceNodeConfig):
    """Configuration for the thermocycler node module."""

    zmq_server_url: str = "tcp://localhost:5555"


class SimThermocyclerNode(SimpleDeviceRestNode):
    """A Rest Node object to control Thermocycler devices."""

    config: SimThermocyclerNodeConfig = SimThermocyclerNodeConfig()
    config_model = SimThermocyclerNodeConfig

    @property
    def interface_class(self) -> type:
        return SimThermocycler

    @property
    def device_name(self) -> str:
        return "thermocycler"

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="open", description="Open thermocycler lid")
    def open(self):
        """Open thermocycler lid."""
        return self._execute_action(self._interface.open, "Open lid")

    @action(name="close", description="Close thermocycler lid")
    def close(self):
        """Close thermocycler lid."""
        return self._execute_action(self._interface.close, "Close lid")

    @action(name="run_program", description="Run a thermocycling program")
    def run_program(
        self,
        program_number: Annotated[int, "Program number to run"],
    ):
        """Run a thermocycling program."""
        success = self._interface.run_program(program_number)
        if not success:
            return ActionFailed(errors="Failed to run thermocycler program")


if __name__ == "__main__":
    thermocycler_node = SimThermocyclerNode()
    thermocycler_node.start_node()
