import os
import signal

from madsci.node_module.helpers import action

from slcore.robots.common.simple_device_node import SimpleDeviceNodeConfig, SimpleDeviceRestNode
from slcore.robots.sealer.sim_sealer_interface import SimSealer


class SimSealerNodeConfig(SimpleDeviceNodeConfig):
    """Configuration for the sealer node module."""

    zmq_server_url: str = "tcp://localhost:5558"


class SimSealerNode(SimpleDeviceRestNode):
    """A Rest Node object to control Sealer devices."""

    config: SimSealerNodeConfig = SimSealerNodeConfig()
    config_model = SimSealerNodeConfig

    @property
    def interface_class(self) -> type:
        return SimSealer

    @property
    def device_name(self) -> str:
        return "sealer"

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="seal", description="Seal a plate")
    def seal(self):
        """Seal a plate."""
        return self._execute_action(self._interface.seal, "Seal")


if __name__ == "__main__":
    sealer_node = SimSealerNode()
    sealer_node.start_node()
