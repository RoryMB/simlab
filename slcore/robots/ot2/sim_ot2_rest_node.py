import os
import signal
from pathlib import Path
from typing import Annotated, Any

from madsci.node_module.helpers import action
from ot2_interface.config import OT2_Config
from ot2_rest_node import OT2Node, OT2NodeConfig

from slcore.robots.ot2.sim_ot2_interface import SimOT2_Driver


class SimOT2NodeConfig(OT2NodeConfig):
    """Configuration for the OT2 node module."""

    resource_server_url: str = "http://localhost:8013"
    "Temporary hack to fix ot2_rest_node.py:49"

    ot2_ip: str = ""
    "Not used in simulation; setting a default value"

    zmq_server_url: str = "tcp://localhost:5556"
    "For Isaac Sim communication"

    python_executable: str = "python"
    "Python executable to use for running protocols"


class SimOT2Node(OT2Node):
    """Node module for Opentrons Robots"""

    ot2_interface: SimOT2_Driver
    config: SimOT2NodeConfig = SimOT2NodeConfig()
    config_model = SimOT2NodeConfig

    # def _exception_handler(self, e: Exception, set_node_errored: bool = True):
    #     """Overrides the default exception handler to force a shutdown."""
    #     super()._exception_handler(e, set_node_errored)
    #     self.logger.log_critical("Error detected in simulation fail-fast mode. Forcing node shutdown.")
    #     os.kill(os.getpid(), signal.SIGTERM)

    def connect_robot(self) -> None:
        """Initialize the OT2 interface"""
        self.ot2_interface = SimOT2_Driver(
            config=OT2_Config(ip=self.config.ot2_ip),
            zmq_server_url=self.config.zmq_server_url,
            python_executable=self.config.python_executable,
        )

        self.logger.log("OT2 node online")

    @action(name="run_protocol", description="run a given opentrons protocol")
    def run_protocol(
        self,
        protocol: Annotated[Path, "Protocol File"],
        parameters: Annotated[dict[str, Any], "Parameters for insertion into the protocol"] = {},
    ):
        """Run a given protocol on the OT2"""
        return super().run_protocol(protocol, parameters)


if __name__ == "__main__":
    sim_ot2_node = SimOT2Node()
    sim_ot2_node.start_node()
