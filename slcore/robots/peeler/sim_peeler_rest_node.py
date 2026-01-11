import os
import signal

from madsci.common.types.action_types import ActionResult
from madsci.node_module.helpers import action

from slcore.robots.common.simple_device_node import SimpleDeviceNodeConfig, SimpleDeviceRestNode
from slcore.robots.peeler.sim_peeler_interface import SimPeeler


class SimPeelerNodeConfig(SimpleDeviceNodeConfig):
    """Configuration for the peeler node module."""

    zmq_server_url: str = "tcp://localhost:5559"


class SimPeelerNode(SimpleDeviceRestNode):
    """A Rest Node object to control Peeler devices."""

    config: SimPeelerNodeConfig = SimPeelerNodeConfig()
    config_model = SimPeelerNodeConfig

    @property
    def interface_class(self) -> type:
        return SimPeeler

    @property
    def device_name(self) -> str:
        return "peeler"

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="peel", description="Peel a plate seal")
    def peel(self) -> ActionResult:
        """Peel a plate seal."""
        return self._execute_action(self._interface.peel, "Peel")


if __name__ == "__main__":
    peeler_node = SimPeelerNode()
    peeler_node.start_node()
