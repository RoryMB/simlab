import json
from typing import Optional

import zmq

from madsci.client.event_client import EventClient


class SimPeeler:
    """Driver Class for the Peeler device."""

    status_code: int = 0

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5559",
        logger: Optional[EventClient] = None,
    ) -> "SimPeeler":
        """Initialize the Peeler ZMQ client."""
        self.logger = logger or EventClient()
        self.zmq_server_url = zmq_server_url

        # Initialize ZMQ client
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.zmq_server_url)

        self.logger.log(f"SimPeeler connected to ZMQ server at {self.zmq_server_url}")

    def __del__(self):
        """Clean up ZMQ resources."""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()

    def disconnect(self) -> None:
        pass

    def send_zmq_command(self, command: dict) -> dict:
        """Send a command via ZMQ and return the response."""
        try:
            # Send command
            self.socket.send_string(json.dumps(command))

            # Receive response with timeout
            if self.socket.poll(5000):  # 5 second timeout
                response_str = self.socket.recv_string()
                response = json.loads(response_str)
                return response
            else:
                return {"status": "error", "message": "Timeout waiting for response"}
        except Exception as e:
            self.logger.log(f"ZMQ command failed: {e}")
            return {"status": "error", "message": str(e)}

    def peel(self) -> bool:
        """Peel a plate seal."""
        self.logger.log("Executing peel operation")

        zmq_command = {"action": "peel"}
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log("Peel operation completed")
        else:
            self.logger.log(f"Peel operation failed: {response.get('message', 'Unknown error')}")

        return success

    def initialize_device(self) -> None:
        """Initialize the device."""
        self.logger.log("Peeler device initialized")
