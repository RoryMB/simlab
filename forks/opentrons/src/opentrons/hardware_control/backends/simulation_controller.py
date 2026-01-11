from __future__ import annotations
import asyncio
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Iterator, Tuple, Sequence, Union
from typing_extensions import Final

try:
    import aionotify  # type: ignore[import-untyped]
except (OSError, ModuleNotFoundError):
    aionotify = None

import opentrons.config
from opentrons_shared_data.pipette.types import PipetteName
from opentrons.config.types import RobotConfig
from opentrons.types import Mount
from ..dev_types import AttachedInstruments, AttachedPipette
from ..module_control import AttachedModulesControl
from ..simulation import ZMQSimulationClient, AxisMapper
from ..types import (
    BoardRevision,
    DoorState,
    EstopState,
    StatusBarState,
    Axis,
    AionotifyEvent,
)

if TYPE_CHECKING:
    from opentrons_shared_data.pipette.types import PipetteModel
    from ..dev_types import (
        AttachedPipette,
        AttachedInstruments,
        InstrumentHardwareConfigs,
    )
    from opentrons.drivers.rpi_drivers.dev_types import GPIODriverLike

MODULE_LOG = logging.getLogger(__name__)


class SimulationController:
    """The simulation instance of the controller for controlling
    simulated hardware via ZMQ.
    """

    @classmethod
    async def build(cls, config: Optional[RobotConfig]) -> SimulationController:
        """Build a SimulationController instance.

        Use this factory method rather than the initializer to handle proper
        simulation client initialization.

        :param config: A loaded robot config.
        """
        instance = cls(config, None)
        await instance.connect()
        return instance

    def __init__(self, config: Optional[RobotConfig], gpio: GPIODriverLike):
        """Build a SimulationController instance.

        Always prefer using :py:meth:`.build` to create an instance of this class.
        """
        if not opentrons.config.IS_ROBOT:
            MODULE_LOG.warning(
                "This is intended to run on a robot, and while it can connect "
                "to a smoothie via a usb/serial adapter unexpected things "
                "using gpios (such as smoothie reset or light management) "
                "will fail. If you are seeing this message and you are "
                "running on a robot, you need to set the RUNNING_ON_PI "
                "environmental variable to 1."
            )

        self.config = config or opentrons.config.robot_configs.load_ot2()

        self._simulation_client = ZMQSimulationClient()
        self._axis_mapper = AxisMapper()
        self._board_revision: Final = BoardRevision.A
        self._cached_fw_version: Optional[str] = "simulation-1.0.0"
        self._module_controls: Optional[AttachedModulesControl] = None

        # Minimal state tracking
        self._door_state = DoorState.CLOSED
        self._estop_state = EstopState.NOT_PRESENT

        # No extra state tracking needed - Controller doesn't track pause state

    @staticmethod
    def _build_event_watcher() -> aionotify.Watcher:
        """Event watcher not needed for simulation."""
        return None

    @property
    def gpio_chardev(self) -> GPIODriverLike:
        """Mock GPIO driver interface for simulation."""
        return None  # type: ignore

    @property
    def board_revision(self) -> BoardRevision:
        return self._board_revision

    @property
    def module_controls(self) -> AttachedModulesControl:
        if not self._module_controls:
            raise AttributeError("Module controls not found.")
        return self._module_controls

    @module_controls.setter
    def module_controls(self, module_controls: AttachedModulesControl) -> None:
        self._module_controls = module_controls

    async def get_serial_number(self) -> Optional[str]:
        """Get simulated robot serial number."""
        return "SIM123456789"

    def start_gpio_door_watcher(
        self,
        loop: asyncio.AbstractEventLoop,
        update_door_state: Any,
    ) -> None:
        """Start door watcher (simulation - no-op)."""
        pass

    async def update_position(self) -> Dict[str, float]:
        """Update position from simulation."""
        joint_positions = await self._simulation_client.get_joint_positions()
        return self._axis_mapper.convert_joint_positions_to_axes(joint_positions)

    def _unhomed_axes(self, axes: Sequence[str]) -> List[str]:
        """Get list of unhomed axes from sequence."""
        homed = self._simulation_client.is_homed(list(axes))
        return [] if homed else list(axes)

    def is_homed(self, axes: Sequence[str]) -> bool:
        """Check if all axes in sequence are homed."""
        return self._simulation_client.is_homed(list(axes))

    async def move(
        self,
        target_position: Dict[str, float],
        home_flagged_axes: bool = True,
        speed: Optional[float] = None,
        axis_max_speeds: Optional[Dict[str, float]] = None,
    ) -> None:
        """Move robot axes to target positions."""
        joint_commands = self._axis_mapper.convert_positions_to_joints(target_position)
        if not joint_commands:
            return
        success = await self._simulation_client.move_joints(joint_commands)
        if not success:
            raise RuntimeError("Failed to execute movement in simulation")

    async def home(self, axes: Optional[List[str]] = None) -> Dict[str, float]:
        """Home specified axes or all axes."""
        success = await self._simulation_client.home_robot()
        if not success:
            raise RuntimeError("Failed to home robot in simulation")
        return await self.update_position()

    async def fast_home(self, axes: Sequence[str], margin: float) -> Dict[str, float]:
        """Fast home with margin (simulation just uses regular home)."""
        return await self.home(list(axes))

    async def _query_mount(
        self, mount: Mount, expected: Union["PipetteModel", PipetteName, None]
    ) -> "AttachedPipette":
        """Query mount for attached pipette (simulation)."""
        instruments = self._simulation_client.get_attached_instruments()
        mount_info = instruments.get(mount.name.lower(), {})

        if mount_info.get("model"):
            return {"config": mount_info.get("config"), "id": mount_info.get("id")}
        else:
            if expected:
                raise RuntimeError(
                    f"mount {mount}: instrument {expected} was"
                    f" requested, but no instrument is present"
                )
            return {"config": None, "id": None}

    async def get_attached_instruments(
        self, expected: Dict[Mount, PipetteName]
    ) -> "AttachedInstruments":
        """Find the instruments attached to our mounts (simulation)."""
        return {
            mount: await self._query_mount(mount, expected.get(mount))
            for mount in Mount.ot2_mounts()
        }

    def set_active_current(self, axis_currents: Dict[Axis, float]) -> None:
        """Set active current for axes (simulation - no-op)."""
        pass

    @contextmanager
    def save_current(self) -> Iterator[None]:
        """Save and restore current settings (simulation - no-op)."""
        yield

    async def _handle_watch_event(self) -> None:
        pass

    async def watch(self, loop: asyncio.AbstractEventLoop) -> None:
        pass

    async def connect(self, port: Optional[str] = None) -> None:
        """Build driver and connect to it."""
        await self._simulation_client.connect()
        await self.update_fw_version()

    @property
    def axis_bounds(self) -> Dict[Axis, Tuple[float, float]]:
        """The (minimum, maximum) bounds for each axis."""
        return {
            Axis.X: (0.0, 418.0),
            Axis.Y: (0.0, 353.0),
            Axis.Z: (0.0, 218.0),
            Axis.A: (0.0, 218.0),
            Axis.B: (0.0, 19.0),
            Axis.C: (0.0, 19.0),
        }

    @property
    def fw_version(self) -> Optional[str]:
        return self._cached_fw_version

    async def update_fw_version(self) -> None:
        """Update firmware version (simulation)."""
        self._cached_fw_version = "simulation-1.0.0"

    async def update_firmware(
        self, filename: str, loop: asyncio.AbstractEventLoop, modeset: bool
    ) -> str:
        """Simulate firmware update."""
        await self.update_fw_version()
        return f"Simulated firmware update with {filename} completed"

    def engaged_axes(self) -> Dict[str, bool]:
        """Get engagement status of all axes."""
        return {"X": True, "Y": True, "Z": True, "A": True, "B": True, "C": True}

    async def disengage_axes(self, axes: List[str]) -> None:
        """Disengage specified axes (simulation - no-op)."""
        pass

    def set_lights(self, button: Optional[bool], rails: Optional[bool]) -> None:
        """Set lights via simulation."""
        # Controller calls gpio_chardev.set_*_light() directly
        # For simulation, we call Isaac Sim directly
        if button is not None:
            self._simulation_client.set_button_light(button)

        if rails is not None:
            self._simulation_client.set_rail_lights(rails)

    def get_lights(self) -> Dict[str, bool]:
        """Get light status from simulation."""
        # Controller calls gpio_chardev.get_*_light() directly
        # For simulation, we query Isaac Sim directly
        return self._simulation_client.get_lights()

    def pause(self) -> None:
        """Pause robot movement."""
        # Controller calls smoothie_driver.pause() directly
        # For simulation, we call Isaac Sim directly
        self._simulation_client.pause_robot()

    def resume(self) -> None:
        """Resume robot movement."""
        # Controller calls smoothie_driver.resume() directly
        # For simulation, we call Isaac Sim directly
        self._simulation_client.resume_robot()

    async def halt(self) -> None:
        """Halt robot movement."""
        # Controller calls smoothie_driver.kill() directly
        # For simulation, send halt command to Isaac Sim
        await self._simulation_client.halt_robot()

    async def hard_halt(self) -> None:
        """Hard halt robot movement."""
        # Hard halt is same as regular halt for physics simulation
        await self.halt()

    async def probe(self, axis: str, distance: float) -> Dict[str, float]:
        """Run a probe and return the new position dict."""
        return self._simulation_client.probe_axis(axis, distance)

    async def clean_up(self) -> None:
        """Clean up simulation resources."""
        if hasattr(self, "_simulation_client"):
            await self._simulation_client.disconnect()

    async def configure_mount(
        self, mount: Mount, config: "InstrumentHardwareConfigs"
    ) -> None:
        """Configure mount with instrument hardware settings (simulation - no-op)."""
        pass
