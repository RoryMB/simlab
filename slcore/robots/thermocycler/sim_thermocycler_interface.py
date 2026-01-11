from typing import Optional

from madsci.client.event_client import EventClient

from slcore.robots.common.zmq_client_base import ZMQClientInterface


class SimThermocycler(ZMQClientInterface):
    """Driver Class for the Thermocycler device."""

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5560",
        logger: Optional[EventClient] = None,
    ) -> "SimThermocycler":
        """Initialize the Thermocycler ZMQ client."""
        super().__init__(zmq_server_url, logger)

    def open(self) -> bool:
        """Open thermocycler lid."""
        return self._execute_simple_action("open")

    def close(self) -> bool:
        """Close thermocycler lid."""
        return self._execute_simple_action("close")

    def run_program(self, program_number: int) -> bool:
        """Run a thermocycling program."""
        self.logger.log(f"Running thermocycler program {program_number}")

        zmq_command = {
            "action": "run_program",
            "program_number": program_number
        }
        response = self.send_zmq_command(zmq_command)

        success = response.get("status") == "success"
        if success:
            self.logger.log(f"Thermocycler program {program_number} completed")
        else:
            self.logger.log(f"Failed to run program: {response.get('message', 'Unknown error')}")

        return success

    def initialize_device(self) -> None:
        """Initialize the device."""
        self.logger.log("Thermocycler device initialized")
