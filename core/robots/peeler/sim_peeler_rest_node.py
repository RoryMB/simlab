import os
import signal
from typing import Optional

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from sim_peeler_interface import SimPeeler


class SimPeelerNodeConfig(RestNodeConfig):
    """Configuration for the peeler node module."""

    zmq_server_url: str = "tcp://localhost:5559"


class SimPeelerNode(RestNode):
    """A Rest Node object to control Peeler devices"""

    peeler_interface: SimPeeler = None
    config: SimPeelerNodeConfig = SimPeelerNodeConfig()
    config_model = SimPeelerNodeConfig

    def startup_handler(self) -> None:
        """Initialize the node."""
        self.peeler_interface = SimPeeler(
            zmq_server_url=self.config.zmq_server_url,
        )
        self.peeler_interface.initialize_device()

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.peeler_interface is not None:
            self.node_state = {
                "peeler_status_code": self.peeler_interface.status_code,
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            }

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="peel", description="Peel a plate seal")
    def peel(self) -> ActionResult:
        """Peel a plate seal."""
        success = self.peeler_interface.peel()
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Peel operation failed"]
            )


if __name__ == "__main__":
    peeler_node = SimPeelerNode()
    peeler_node.start_node()