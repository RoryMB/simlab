#! /usr/bin/env python3
"""Simulated OT2 Node Module implementation using ZMQ backend"""

import traceback
from pathlib import Path
from typing import Any, Annotated

from madsci.node_module.helpers import action
from madsci.common.types.action_types import ActionResult, ActionSucceeded, ActionFailed
from ot2_rest_node import OT2Node, OT2NodeConfig
from sim_ot2_driver import SimOT2_Driver
from ot2_interface.config import OT2_Config


class SimOT2NodeConfig(OT2NodeConfig):
    """Configuration for the simulated OT2 node module."""

    resource_server_url: str = "http://localhost:8013"
    "Temporary hack to fix ot2_rest_node.py:49"

    ot2_ip: str = ""
    "We don't use the ot2_ip in the simulated version"

    zmq_server_url: str = "tcp://localhost:5556"
    "ZMQ server URL for Isaac Sim communication"

    python_executable: str = "python"
    "Python executable to use for running protocols"


class SimOT2Node(OT2Node):
    """Simulated node module for Opentrons Robots using ZMQ backend"""

    config: SimOT2NodeConfig = SimOT2NodeConfig()
    config_model = SimOT2NodeConfig

    def startup_handler(self) -> None:
        """Initialize the simulated OT2 node."""
        self.logger.log("Simulated OT2 node initializing...")
        # Call parent startup handler to set up resources and folders
        super().startup_handler()
        self.logger.log("Simulated OT2 node initialized!")

    def state_handler(self) -> None:
        """Update node state with simulation-specific info."""
        super().state_handler()
        if self.ot2_interface is not None:
            self.node_state.update({
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            })

    def connect_robot(self) -> None:
        """Initialize the simulated OT2 interface"""
        try:
            # Create config for compatibility
            ot2_config = OT2_Config(ip=self.config.ot2_ip)

            # Initialize simulation driver instead of real driver
            self.ot2_interface = SimOT2_Driver(
                config=ot2_config,
                zmq_server_url=self.config.zmq_server_url,
                python_executable=self.config.python_executable
            )

            self.logger.log("Simulated OT2 node online")

        except Exception as error_msg:
            self.node_status.errored = True
            self.logger.log(f"Error connecting to simulated robot: {error_msg}")

    def execute(self, protocol_path, payload=None, resource_config=None):
        """Execute protocol using simulation driver with protocol_path passed through."""
        protocol_file_path = Path(protocol_path)
        self.logger.log(f"Simulated execution: {protocol_file_path.resolve()}")

        try:
            protocol_id, run_id = self.ot2_interface.transfer(protocol_file_path)
            self.logger.log(f"Simulated OT2 {self.node_definition.node_name} protocol validated")

            self.run_id = run_id
            # Pass the protocol path to the simulation driver's execute method
            resp = self.ot2_interface.execute(run_id, protocol_path=protocol_file_path)
            self.run_id = None

            print(f"Simulation execution result: {resp}")

            if resp["data"]["status"] == "succeeded":
                self.logger.log(f"Simulated OT2 {self.node_definition.node_name} succeeded")
                return "succeeded", "Protocol executed successfully in simulation", run_id
            elif resp["data"]["status"] == "stopped":
                self.logger.log(f"Simulated OT2 {self.node_definition.node_name} stopped")
                return "stopped", "Protocol stopped in simulation", run_id
            else:
                self.logger.log(f"Simulated OT2 {self.node_definition.node_name} failed")
                return "failed", f"Protocol failed in simulation: {resp['data']}", run_id

        except Exception as err:
            error_msg = f"Simulation error: {traceback.format_exc()}"
            self.logger.log(error_msg)
            return False, error_msg, None

    @action
    def run_protocol(
        self,
        protocol: Annotated[Path, "Protocol File"],
        parameters: Annotated[dict[str, Any], "Parameters for insertion into the protocol"] = {},
    ) -> ActionResult:
        """
        Run a given protocol on the simulated OT-2
        """
        try:
            # Call the parent's run_protocol logic but return proper ActionResult
            if protocol:
                with protocol.open(mode="r") as f:
                    file_text = f.read()
                    for key in parameters.keys():
                        file_text = file_text.replace("$" + key, str(parameters[key]))
                with protocol.open(mode="w") as f:
                    f.write(file_text)
                    
                response_flag, response_msg, run_id = self.execute(protocol, parameters)
                
                if response_flag == "succeeded":
                    self.logger.log("Protocol executed successfully")
                    return ActionSucceeded(data={"run_id": run_id, "message": response_msg})
                elif response_flag == "stopped":
                    self.logger.log("Protocol execution stopped")
                    return ActionFailed(data={"run_id": run_id, "message": response_msg})
                else:
                    self.logger.log(f"Protocol execution failed: {response_msg}")
                    return ActionFailed(data={"run_id": run_id, "message": response_msg})
            else:
                return ActionFailed(data={"message": "No protocol file provided"})
                
        except Exception as e:
            error_msg = f"Error in run_protocol: {traceback.format_exc()}"
            self.logger.log(error_msg)
            return ActionFailed(data={"message": error_msg})


if __name__ == "__main__":
    sim_ot2_node = SimOT2Node()
    sim_ot2_node.start_node()