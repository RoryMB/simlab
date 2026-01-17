"""Base class for ZMQ robot/device client interfaces."""

import json
from abc import ABC

import zmq
from madsci.client.event_client import EventClient


class ZMQClientInterface(ABC):
    """Base class for all ZMQ robot/device client interfaces.

    Provides common ZMQ connection management and command sending functionality
    that is shared across all robot interface implementations.
    """

    status_code: int = 0

    def __init__(
        self,
        zmq_server_url: str,
        env_id: int,
        robot_type: str,
        logger=None,
        timeout_ms: int = 5000,
    ):
        """Initialize ZMQ DEALER client connection.

        Args:
            zmq_server_url: ZMQ server URL (e.g., "tcp://localhost:5555")
            env_id: Environment ID for routing (0-N)
            robot_type: Robot type identifier (e.g., "pf400", "peeler")
            logger: Optional EventClient logger instance
            timeout_ms: Timeout in milliseconds for ZMQ commands (default: 5000)
        """
        self.logger = logger or EventClient()
        self.zmq_server_url = zmq_server_url
        self.env_id = env_id
        self.robot_type = robot_type
        self.timeout_ms = timeout_ms
        self.identity = f"env_{env_id}.{robot_type}"
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.identity)
        self.socket.connect(self.zmq_server_url)
        self.logger.log(f"{self.__class__.__name__} connected to {zmq_server_url} with identity {self.identity}")

    def __del__(self):
        """Clean up ZMQ resources."""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()

    def disconnect(self) -> None:
        """Disconnect from ZMQ server (no-op for compatibility)."""
        pass

    def send_zmq_command(self, command: dict) -> dict:
        """Send a command via ZMQ DEALER and return the response.

        Args:
            command: Dictionary containing the command to send

        Returns:
            Response dictionary from the server, or error dict on failure
        """
        try:
            # DEALER sends: [empty, message]
            self.socket.send_multipart([b"", json.dumps(command).encode()])
            if self.socket.poll(self.timeout_ms):
                # DEALER receives: [empty, response]
                _, response_bytes = self.socket.recv_multipart()
                return json.loads(response_bytes.decode())
            else:
                return {"status": "error", "message": f"Timeout after {self.timeout_ms}ms"}
        except Exception as e:
            self.logger.log(f"ZMQ command failed: {e}")
            return {"status": "error", "message": str(e)}

    def _execute_simple_action(self, action_name: str) -> bool:
        """Execute a simple ZMQ action and return success status.

        Args:
            action_name: Name of the action to execute

        Returns:
            True if action succeeded, False otherwise
        """
        self.logger.log(f"Executing {action_name} operation")
        response = self.send_zmq_command({"action": action_name})
        success = response.get("status") == "success"
        if success:
            self.logger.log(f"{action_name.capitalize()} operation completed")
        else:
            self.logger.log(f"{action_name} failed: {response.get('message', 'Unknown error')}")
        return success
