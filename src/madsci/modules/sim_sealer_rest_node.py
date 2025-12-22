import os
import signal
from typing import Optional

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from sim_sealer_interface import SimSealer


class SimSealerNodeConfig(RestNodeConfig):
    """Configuration for the sealer node module."""

    zmq_server_url: str = "tcp://localhost:5558"


class SimSealerNode(RestNode):
    """A Rest Node object to control Sealer devices"""

    sealer_interface: SimSealer = None
    config: SimSealerNodeConfig = SimSealerNodeConfig()
    config_model = SimSealerNodeConfig

    def startup_handler(self) -> None:
        """Initialize the node."""
        self.sealer_interface = SimSealer(
            zmq_server_url=self.config.zmq_server_url,
        )
        self.sealer_interface.initialize_device()

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.sealer_interface is not None:
            self.node_state = {
                "sealer_status_code": self.sealer_interface.status_code,
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            }

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="seal", description="Seal a plate")
    def seal(self) -> ActionResult:
        """Seal a plate."""
        success = self.sealer_interface.seal()
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Seal operation failed"]
            )


if __name__ == "__main__":
    sealer_node = SimSealerNode()
    sealer_node.start_node()