import os
import subprocess
import time
import traceback
from pathlib import Path
from typing import Annotated

from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded
from madsci.node_module.helpers import action
from ot2_interface.config import OT2_Config, PathLike
from ot2_interface.ot2_driver_http import OT2_Driver
from ot2_rest_node import OT2Node, OT2NodeConfig


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


class SimOT2_Driver(OT2_Driver):
    """Driver for simulated OT-2 robot that executes protocols locally with ZMQ backend."""

    def __init__(
        self,
        config: OT2_Config,
        zmq_server_url: str = "tcp://localhost:5556",
        python_executable: str = None,
        **kwargs
    ) -> None:
        """Initialize simulated OT-2 driver.

        Parameters
        ----------
        config : OT2_Config
            OT-2 configuration
        zmq_server_url : str
            ZMQ server URL for Isaac Sim communication
        python_executable : str
            Path to python executable to use for running protocols
        """
        # Store simulation-specific parameters
        self.zmq_server_url = zmq_server_url
        self.python_executable = python_executable or "python"

        # Initialize parent class (but skip the HTTP connection test)
        self.config = config
        print(f"SimOT2_Driver initialized with ZMQ server: {self.zmq_server_url}")

    def transfer(self, protocol_path: PathLike) -> tuple[str, str]:
        """Validate protocol file exists locally (replaces HTTP transfer)."""
        protocol_path = Path(protocol_path)

        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol file not found: {protocol_path}")

        # Note: MADSci passes temporary files without .py extension, so we don't check suffix
        # The file contents are already validated by MADSci
        print(f"Protocol file received: {protocol_path}")

        # Generate dummy IDs for compatibility with MADSci interface
        protocol_id = f"sim_protocol_{int(time.time())}"
        run_id = f"sim_run_{int(time.time())}"

        return protocol_id, run_id

    def execute(self, run_id: str, protocol_path: PathLike = None) -> dict[str, dict[str, str]]:
        """Execute protocol using hacked opentrons package with ZMQ backend."""
        if protocol_path is None:
            raise ValueError("protocol_path must be provided for simulation execution")

        protocol_path = Path(protocol_path)

        print(f"Executing protocol: {protocol_path}")
        print(f"Using ZMQ server: {self.zmq_server_url}")

        # OpenTrons requires .py extension - copy temp file if needed
        temp_py_path = None
        if not protocol_path.suffix == ".py":
            import shutil
            import tempfile
            # Create a temporary .py file
            temp_py_file = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
            temp_py_file.close()
            temp_py_path = Path(temp_py_file.name)

            # Copy the content
            shutil.copy2(protocol_path, temp_py_path)
            protocol_path = temp_py_path
            print(f"Copied to temporary .py file: {protocol_path}")

        # Set up environment variables for hacked opentrons package
        env = os.environ.copy()
        env['OPENTRONS_SIMULATION_MODE'] = 'zmq'
        env['OT2_SIMULATION_SERVER'] = self.zmq_server_url

        try:
            # Execute the protocol using OpenTrons execute function
            result = subprocess.run(
                [self.python_executable, "-m", "opentrons.execute", str(protocol_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            print(f"Protocol execution stdout: {result.stdout}")
            if result.stderr:
                print(f"Protocol execution stderr: {result.stderr}")

            if result.returncode == 0:
                print("Protocol execution succeeded")
                return {
                    "data": {
                        "status": "succeeded",
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                }
            else:
                print(f"Protocol execution failed with return code: {result.returncode}")
                return {
                    "data": {
                        "status": "failed",
                        "error": f"Process failed with code {result.returncode}",
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                }

        except subprocess.TimeoutExpired:
            print("Protocol execution timed out")
            return {
                "data": {
                    "status": "failed",
                    "error": "Protocol execution timed out after 5 minutes"
                }
            }
        except Exception as e:
            print(f"Error executing protocol: {e}")
            return {
                "data": {
                    "status": "failed",
                    "error": str(e)
                }
            }
        finally:
            # Clean up temporary .py file if created
            if temp_py_path and temp_py_path.exists():
                temp_py_path.unlink()
                print(f"Cleaned up temporary file: {temp_py_path}")


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
        parameters: Annotated[dict[str, any], "Parameters for insertion into the protocol"] = {},
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
