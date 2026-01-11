from typing import Optional

from madsci.client.event_client import EventClient

from slcore.robots.common.zmq_client_base import ZMQClientInterface


class SimHidex(ZMQClientInterface):
    """Driver Class for the Hidex plate reader device."""

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5561",
        logger: Optional[EventClient] = None,
    ) -> "SimHidex":
        """Initialize the Hidex ZMQ client."""
        super().__init__(zmq_server_url, logger)

    def open(self) -> bool:
        """Open Hidex drawer."""
        return self._execute_simple_action("open")

    def close(self) -> bool:
        """Close Hidex drawer."""
        return self._execute_simple_action("close")

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
