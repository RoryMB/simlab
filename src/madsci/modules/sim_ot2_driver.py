"""Driver for simulated OT-2 robot using hacked opentrons package and ZMQ."""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Tuple

from ot2_interface.config import OT2_Config, PathLike
from ot2_interface.ot2_driver_http import OT2_Driver, RobotStatus, RunStatus


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

    def transfer(self, protocol_path: PathLike) -> Tuple[str, str]:
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

    def execute(self, run_id: str, protocol_path: PathLike = None) -> Dict[str, Dict[str, str]]:
        """Execute protocol using hacked opentrons package with ZMQ backend."""
        if protocol_path is None:
            raise ValueError("protocol_path must be provided for simulation execution")
            
        protocol_path = Path(protocol_path)
        
        print(f"Executing protocol: {protocol_path}")
        print(f"Using ZMQ server: {self.zmq_server_url}")
        
        # Set up environment variables for hacked opentrons package
        env = os.environ.copy()
        env['OPENTRONS_SIMULATION_MODE'] = 'zmq'
        env['OT2_SIMULATION_SERVER'] = self.zmq_server_url
        
        try:
            # Execute the protocol as a subprocess
            result = subprocess.run(
                [self.python_executable, str(protocol_path)],
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