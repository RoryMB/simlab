import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ot2_interface.config import OT2_Config, PathLike
from ot2_interface.ot2_driver_http import OT2_Driver, RobotStatus, RunStatus


class SimOT2_Driver(OT2_Driver):
    """Driver code for the OT2 that executes protocols locally with ZMQ communications."""

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

        # Storage for protocol paths by run_id
        self._stored_protocols = {}

        # Initialize parent class (but skip the HTTP connection test)
        self.config = config
        print(f"SimOT2_Driver initialized with ZMQ server: {self.zmq_server_url}")

    def compile_protocol(self, config_path, resource_file=None, resource_path=None, payload=None, protocol_out_path=None):
        """Compile the protocols via protopiler"""
        # Protopiler is being deprecated, so we do not support it
        # Simply assume all protocols are already Python files
        return config_path, resource_file

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

        # Store protocol path for later execution
        self._stored_protocols[run_id] = protocol_path

        return protocol_id, run_id

    def execute(self, run_id: str) -> dict[str, dict[str, str]]:
        """Execute protocol using hacked opentrons package with ZMQ backend."""
        if run_id not in self._stored_protocols:
            raise ValueError(f"No protocol found for run_id: {run_id}")

        protocol_path = Path(self._stored_protocols[run_id])

        print(f"Executing protocol: {protocol_path}")
        print(f"Using ZMQ server: {self.zmq_server_url}")

        # OpenTrons requires .py extension - copy temp file if needed
        temp_py_path = None
        if not protocol_path.suffix == ".py":
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

            # Clean up stored protocol path
            if run_id in self._stored_protocols:
                del self._stored_protocols[run_id]

    def pause(self, run_id):
        """Simulation doesn't support pause - return success response."""
        return {"status_code": 200}

    def resume(self, run_id):
        """Simulation doesn't support resume - return success response."""
        return {"status_code": 200}

    def cancel(self, run_id):
        """Simulation doesn't support cancel - return success response."""
        return {"status_code": 200}

    def check_run_status(self, run_id):
        """Return SUCCEEDED status for simulation."""
        return RunStatus.SUCCEEDED

    def get_run(self, run_id):
        """Return basic run info for simulation."""
        return {"data": {"status": "succeeded", "id": run_id}}

    def get_run_log(self, run_id):
        """Return empty command log for simulation."""
        return {"data": {"status": "succeeded"}, "commands": {"data": []}}

    def get_runs(self):
        """Return empty runs list for simulation."""
        return []

    def get_robot_status(self):
        """Return IDLE status for simulation."""
        return RobotStatus.IDLE

    def reset_robot_data(self):
        """No-op for simulation."""
        pass

    def change_lights_status(self, status=False):
        """No-op for simulation."""
        pass

    def send_request(self, request_extension, **kwargs):
        """Not supported in simulation."""
        raise NotImplementedError("send_request not supported in simulation")

    def stream(self, command, params, run_id=None, execute=True, intent="setup"):
        """Not supported in simulation."""
        raise NotImplementedError("stream not supported in simulation")
