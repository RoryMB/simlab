from typing import Optional

from madsci.client.event_client import EventClient

from slcore.robots.common.zmq_client_base import ZMQClientInterface


class SimPeeler(ZMQClientInterface):
    """Driver Class for the Peeler device."""

    def __init__(
        self,
        zmq_server_url: str = "tcp://localhost:5555",
        env_id: int = 0,
        logger: Optional[EventClient] = None,
    ) -> "SimPeeler":
        """Initialize the Peeler ZMQ client."""
        super().__init__(zmq_server_url, env_id, "peeler", logger)

    def peel(self) -> bool:
        """Peel a plate seal."""
        return self._execute_simple_action("peel")

    def initialize_device(self) -> None:
        """Initialize the device."""
        self.logger.log("Peeler device initialized")
