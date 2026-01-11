"""
ZMQ client for communicating with external physics simulation.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
import zmq

logger = logging.getLogger(__name__)


class ZMQSimulationClient:
    """Client for communicating with ZMQ-based physics simulation."""

    def __init__(self, server_url: Optional[str] = None):
        """Initialize ZMQ client and connect immediately.

        Args:
            server_url: URL of simulation server. If None, uses environment variable
                       OT2_SIMULATION_SERVER or defaults to tcp://localhost:5556
        """
        self.server_url = (
            server_url or
            os.environ.get("OT2_SIMULATION_SERVER", "tcp://localhost:5556")
        )
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.server_url)

        # Set timeout for recv operations
        self.socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout

        logger.info(f"Connected to OT-2 simulation server at {self.server_url}")

    async def connect(self) -> None:
        """Connect is a no-op since we connect in __init__."""
        pass

    async def disconnect(self) -> None:
        """Disconnect from the simulation server."""
        if self.socket:
            self.socket.close()
            self.socket = None

        if self.context:
            self.context.term()
            self.context = None

        logger.info("Disconnected from OT-2 simulation server")

    def _send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to the simulation server and get response.

        Args:
            command: Command dictionary to send

        Returns:
            Response dictionary from server

        Raises:
            RuntimeError: If communication fails
        """
        try:
            # Send command
            message = json.dumps(command)
            self.socket.send_string(message)

            # Wait for response
            response_str = self.socket.recv_string()
            response = json.loads(response_str)

            logger.debug(f"Sent: {command}, Received: {response}")

            return response

        except zmq.Again:
            raise RuntimeError("Simulation server response timeout")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from server: {e}")
        except Exception as e:
            raise RuntimeError(f"Communication error: {e}")

    async def move_joints(self, joint_commands: List[Dict[str, Any]]) -> bool:
        """Move multiple joints simultaneously."""
        command = {
            "action": "move_joints",
            "joint_commands": joint_commands,
        }

        response = self._send_command(command)
        return response.get("status") == "success"

    async def get_joint_positions(self) -> Dict[str, float]:
        """Get current joint positions."""
        command = {"action": "get_joints"}
        response = self._send_command(command)

        if response.get("status") == "success":
            return response.get("joint_positions", {})
        else:
            raise RuntimeError(f"Failed to get joint positions: {response}")

    async def home_robot(self) -> bool:
        """Home all robot joints."""
        command = {"action": "home"}
        response = self._send_command(command)
        return response.get("status") == "success"

    def is_homed(self, axes: List[str]) -> bool:
        """Check if specified axes are homed."""
        command = {
            "action": "is_homed",
            "axes": axes,
        }
        response = self._send_command(command)

        if response.get("status") == "success":
            return response.get("homed", False)
        else:
            raise RuntimeError(f"Failed to check homed status: {response}")

    def probe_axis(self, axis: str, distance: float) -> Dict[str, float]:
        """Run a probe on specified axis."""
        command = {
            "action": "probe",
            "axis": axis,
            "distance": distance,
        }
        response = self._send_command(command)

        if response.get("status") == "success":
            return response.get("position", {})
        else:
            raise RuntimeError(f"Failed to probe axis {axis}: {response}")

    def get_attached_instruments(self) -> Dict[str, Any]:
        """Get attached instruments from simulation."""
        command = {"action": "get_attached_instruments"}
        response = self._send_command(command)

        if response.get("status") == "success":
            return response.get("instruments", {})
        else:
            raise RuntimeError(f"Failed to get attached instruments: {response}")

    def set_button_light(self, state: bool) -> bool:
        """Set button light state in simulation."""
        command = {
            "action": "set_button_light",
            "state": state,
        }
        response = self._send_command(command)
        return response.get("status") == "success"

    def set_rail_lights(self, state: bool) -> bool:
        """Set rail lights state in simulation."""
        command = {
            "action": "set_rail_lights",
            "state": state,
        }
        response = self._send_command(command)
        return response.get("status") == "success"

    def get_lights(self) -> Dict[str, bool]:
        """Get current light states from simulation."""
        command = {"action": "get_lights"}
        response = self._send_command(command)

        if response.get("status") == "success":
            return response.get("lights", {"button": False, "rails": False})
        else:
            raise RuntimeError(f"Failed to get lights: {response}")

    def pause_robot(self) -> bool:
        """Pause current robot movement."""
        command = {"action": "pause"}
        response = self._send_command(command)
        return response.get("status") == "success"

    def resume_robot(self) -> bool:
        """Resume paused robot movement."""
        command = {"action": "resume"}
        response = self._send_command(command)
        return response.get("status") == "success"

    async def halt_robot(self) -> bool:
        """Stop current robot movement."""
        command = {"action": "halt"}
        response = self._send_command(command)
        return response.get("status") == "success"
