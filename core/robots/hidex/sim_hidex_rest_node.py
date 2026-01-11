import os
import signal
from typing import Annotated, Optional

from madsci.common.types.action_types import ActionResult, ActionStatus
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from sim_hidex_interface import SimHidex


class SimHidexNodeConfig(RestNodeConfig):
    """Configuration for the Hidex node module."""

    zmq_server_url: str = "tcp://localhost:5561"


class SimHidexNode(RestNode):
    """A Rest Node object to control Hidex plate reader devices"""

    hidex_interface: SimHidex = None
    config: SimHidexNodeConfig = SimHidexNodeConfig()
    config_model = SimHidexNodeConfig

    def startup_handler(self) -> None:
        """Initialize the node."""
        self.hidex_interface = SimHidex(
            zmq_server_url=self.config.zmq_server_url,
        )
        self.hidex_interface.initialize_device()

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.hidex_interface is not None:
            self.node_state = {
                "hidex_status_code": self.hidex_interface.status_code,
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            }

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    @action(name="open", description="Open Hidex drawer")
    def open(self) -> ActionResult:
        """Open Hidex drawer."""
        success = self.hidex_interface.open()
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Failed to open Hidex drawer"]
            )

    @action(name="close", description="Close Hidex drawer")
    def close(self) -> ActionResult:
        """Close Hidex drawer."""
        success = self.hidex_interface.close()
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Failed to close Hidex drawer"]
            )

    @action(name="run_assay", description="Run a plate reader assay")
    def run_assay(
        self,
        assay_name: Annotated[str, "Name of the assay to run"],
    ) -> ActionResult:
        """Run a plate reader assay."""
        success = self.hidex_interface.run_assay(assay_name)
        if success:
            return ActionResult(status=ActionStatus.SUCCEEDED)
        else:
            return ActionResult(
                status=ActionStatus.FAILED,
                errors=["Failed to run Hidex assay"]
            )


if __name__ == "__main__":
    hidex_node = SimHidexNode()
    hidex_node.start_node()