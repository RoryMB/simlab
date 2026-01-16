"""Base class for simple single-action devices (sealer, peeler, etc.)."""

from abc import abstractmethod
from typing import Any

from madsci.common.types.action_types import ActionFailed
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.rest_node_module import RestNode


class SimpleDeviceNodeConfig(RestNodeConfig):
    """Configuration for simple device nodes."""

    zmq_server_url: str = "tcp://localhost:5555"


class SimpleDeviceRestNode(RestNode):
    """Base class for simple single-action devices (sealer, peeler, etc.).

    Subclasses must:
    - Define interface_class property returning the interface class to instantiate
    - Define device_name property returning the device name for logging/state
    - Define their own @action decorated methods
    """

    config: SimpleDeviceNodeConfig
    _interface: Any = None

    @property
    @abstractmethod
    def interface_class(self) -> type:
        """Return the interface class to instantiate."""
        pass

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Return device name for logging/state."""
        pass

    def startup_handler(self) -> None:
        """Initialize the device interface."""
        self._interface = self.interface_class(
            zmq_server_url=self.config.zmq_server_url
        )
        self._interface.initialize_device()

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self._interface is not None:
            self.node_state = {
                f"{self.device_name}_status_code": self._interface.status_code,
                "simulation_mode": True,
                "zmq_server_url": self.config.zmq_server_url,
            }

    def _execute_action(self, method: callable, action_name: str):
        """Execute an interface method and return ActionFailed on error.

        Args:
            method: The interface method to call (e.g., self._interface.seal)
            action_name: Name of the action for error messages

        Returns:
            None on success, ActionFailed on failure
        """
        success = method()
        if not success:
            return ActionFailed(errors=f"{action_name} operation failed")
