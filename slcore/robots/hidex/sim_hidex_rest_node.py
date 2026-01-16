import os
import signal
from typing import Annotated

from madsci.common.types.action_types import ActionFailed
from madsci.node_module.helpers import action

from slcore.robots.common.simple_device_node import SimpleDeviceNodeConfig, SimpleDeviceRestNode
from slcore.robots.hidex.sim_hidex_interface import SimHidex


class SimHidexNodeConfig(SimpleDeviceNodeConfig):
    """Configuration for the Hidex node module."""

    zmq_server_url: str = "tcp://localhost:5561"


class SimHidexNode(SimpleDeviceRestNode):
    """A Rest Node object to control Hidex plate reader devices."""

    config: SimHidexNodeConfig = SimHidexNodeConfig()
    config_model = SimHidexNodeConfig

    @property
    def interface_class(self) -> type:
        return SimHidex

    @property
    def device_name(self) -> str:
        return "hidex"

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="open", description="Open Hidex drawer")
    def open(self):
        """Open Hidex drawer."""
        return self._execute_action(self._interface.open, "Open drawer")

    @action(name="close", description="Close Hidex drawer")
    def close(self):
        """Close Hidex drawer."""
        return self._execute_action(self._interface.close, "Close drawer")

    @action(name="run_assay", description="Run a plate reader assay")
    def run_assay(
        self,
        assay_name: Annotated[str, "Name of the assay to run"],
    ):
        """Run a plate reader assay."""
        success = self._interface.run_assay(assay_name)
        if not success:
            return ActionFailed(errors="Failed to run Hidex assay")


if __name__ == "__main__":
    hidex_node = SimHidexNode()
    hidex_node.start_node()
