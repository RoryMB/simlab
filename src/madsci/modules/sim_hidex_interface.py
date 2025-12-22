import json
from typing import Optional

import zmq

from madsci.client.event_client import EventClient


class SimHidex:
    """Driver Class for the Hidex plate reader device."""

    status_code: int = 0

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5561",
        logger: Optional[EventClient] = None,
    ) -> "SimHidex":
        """Initialize the Hidex ZMQ client."""
        self.logger = logger or EventClient()
        self.zmq_server_url = zmq_server_url

        # Initialize ZMQ client
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.zmq_server_url)

        self.logger.log(f"SimHidex connected to ZMQ server at {self.zmq_server_url}")

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

    def open(self) -> bool:
        """Open Hidex drawer."""
        self.logger.log("Opening Hidex drawer")

        zmq_command = {"action": "open"}
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log("Hidex drawer opened")
        else:
            self.logger.log(f"Failed to open drawer: {response.get('message', 'Unknown error')}")

        return success

    def close(self) -> bool:
        """Close Hidex drawer."""
        self.logger.log("Closing Hidex drawer")

        zmq_command = {"action": "close"}
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log("Hidex drawer closed")
        else:
            self.logger.log(f"Failed to close drawer: {response.get('message', 'Unknown error')}")

        return success

    def run_assay(self, assay_name: str) -> bool:
        """Run a plate reader assay."""
        self.logger.log(f"Running Hidex assay {assay_name}")

        zmq_command = {
            "action": "run_assay",
            "assay_name": assay_name
        }
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log(f"Hidex assay {assay_name} completed")
        else:
            self.logger.log(f"Failed to run assay: {response.get('message', 'Unknown error')}")

        return success

    def initialize_device(self) -> None:
        """Initialize the device."""
        self.logger.log("Hidex device initialized")
