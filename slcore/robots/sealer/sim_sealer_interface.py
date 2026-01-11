from typing import Optional

from madsci.client.event_client import EventClient

from slcore.robots.common.zmq_client_base import ZMQClientInterface


class SimSealer(ZMQClientInterface):
    """Driver Class for the Sealer device."""

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5558",
        logger: Optional[EventClient] = None,
    ) -> "SimSealer":
        """Initialize the Sealer ZMQ client."""
        super().__init__(zmq_server_url, logger)

    def seal(self) -> bool:
        """Seal a plate."""
        return self._execute_simple_action("seal")

    def initialize_device(self) -> None:
        """Initialize the device."""
        self.logger.log("Sealer device initialized")
