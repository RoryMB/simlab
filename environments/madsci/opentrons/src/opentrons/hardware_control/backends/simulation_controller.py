"""
Simulation controller that replaces the hardware Controller for ZMQ-based simulation.
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any, Tuple, Sequence, cast, TYPE_CHECKING

from opentrons.config.types import RobotConfig
from opentrons.types import Mount
from ..types import (
    Axis, 
    BoardRevision, 
    DoorState,
    EstopState,
    StatusBarState,
    SubSystemState,
)
from ..simulation import ZMQSimulationClient, AxisMapper

if TYPE_CHECKING:
    from ..dev_types import (
        AttachedPipette,
        AttachedInstruments, 
        InstrumentHardwareConfigs,
    )

logger = logging.getLogger(__name__)


class SimulationController:
    """Simulation controller that sends commands to ZMQ simulation server."""
    
    @classmethod
    async def build(cls, config: Optional[RobotConfig]) -> "SimulationController":
        """Build a SimulationController instance.
        
        Args:
            config: Robot configuration (optional)
            
        Returns:
            SimulationController instance
        """
        instance = cls(config)
        await instance._connect()
        return instance
    
    def __init__(self, config: Optional[RobotConfig]):
        """Initialize simulation controller.
        
        Args:
            config: Robot configuration
        """
        self.config = config
        self._simulation_client = ZMQSimulationClient()
        self._axis_mapper = AxisMapper()
        self._connected = False
        
        # State tracking
        self._current_position = {}
        self._lights_on = False
        self._door_state = DoorState.CLOSED
        self._estop_state = EstopState.NOT_PRESENT
        
        logger.info("SimulationController initialized")
    
    async def _connect(self) -> None:
        """Connect to the simulation server."""
        await self._simulation_client.connect()
        self._connected = True
        logger.info("Connected to simulation server")
    
    async def connect(self, port: Optional[str] = None) -> None:
        """Connect method for compatibility with Controller interface."""
        if not self._connected:
            await self._connect()
    
    async def disconnect(self) -> None:
        """Disconnect from simulation server."""
        if self._connected:
            await self._simulation_client.disconnect()
            self._connected = False
            logger.info("Disconnected from simulation server")
    
    # Core movement methods
    
    async def move(
        self,
        target_position: Dict[str, float],
        home_flagged_axes: bool = True,
        speed: Optional[float] = None,
        axis_max_speeds: Optional[Dict[str, float]] = None,
    ) -> None:
        """Move robot axes to target positions.
        
        Args:
            target_position: Dictionary mapping axis names to positions in mm
            home_flagged_axes: Whether to home flagged axes first (ignored in simulation)
            speed: Movement speed in mm/min (optional)
            axis_max_speeds: Max speeds per axis (optional)
        """
        logger.info(f"SimulationController.move: {target_position}")
        
        # Convert Opentrons axes to joint commands
        joint_commands = self._axis_mapper.convert_positions_to_joints(target_position)
        
        if not joint_commands:
            logger.warning("No valid joint commands generated from target positions")
            return
        
        # Send to simulation
        success = await self._simulation_client.move_joints(joint_commands)
        
        if success:
            # Update internal position tracking
            self._current_position.update(target_position)
            logger.info(f"Movement completed: {len(joint_commands)} joints moved")
        else:
            logger.error("Simulation movement failed")
            raise RuntimeError("Failed to execute movement in simulation")
    
    async def home(self, axes: Optional[List[str]] = None) -> Dict[str, float]:
        """Home specified axes or all axes.
        
        Args:
            axes: List of axis names to home, or None for all axes
            
        Returns:
            Dictionary of final positions after homing
        """
        logger.info(f"Homing axes: {axes or 'all'}")
        
        if axes is None:
            # Home all axes
            success = await self._simulation_client.home_robot()
            if success:
                # Update to home positions
                self._current_position.update(self._axis_mapper.OPENTRONS_HOME_POSITIONS)
        else:
            # Home specific axes
            home_positions = {}
            for axis in axes:
                if axis in self._axis_mapper.OPENTRONS_HOME_POSITIONS:
                    home_positions[axis] = self._axis_mapper.OPENTRONS_HOME_POSITIONS[axis]
            
            if home_positions:
                await self.move(home_positions)
        
        return self._current_position.copy()
    
    async def current_position(
        self, 
        mount: Mount, 
        refresh: bool = False
    ) -> Dict[str, float]:
        """Get current position of mount axes.
        
        Args:
            mount: Mount to get position for
            refresh: Whether to refresh from hardware (ignored in simulation)
            
        Returns:
            Dictionary mapping axis names to positions in mm
        """
        if refresh or not self._current_position:
            # Get positions from simulation
            try:
                joint_positions = await self._simulation_client.get_joint_positions()
                # Convert back to Opentrons axes - simplified for now
                logger.debug(f"Current joint positions: {joint_positions}")
            except Exception as e:
                logger.warning(f"Failed to get positions from simulation: {e}")
        
        return self._current_position.copy()
    
    # Pipette and tip management
    
    async def pick_up_tip(
        self,
        mount: Mount, 
        tip_length: float,
        presses: Optional[int] = None,
        increment: Optional[float] = None,
    ) -> None:
        """Simulate tip pickup.
        
        Args:
            mount: Mount to pick up tip on
            tip_length: Length of tip in mm
            presses: Number of pickup attempts
            increment: Distance increment per press
        """
        mount_name = "left" if mount == Mount.LEFT else "right"
        logger.info(f"Picking up tip on {mount_name} mount")
        
        success = await self._simulation_client.pick_up_tip(mount_name)
        if not success:
            raise RuntimeError(f"Failed to pick up tip on {mount_name} mount")
    
    async def drop_tip(self, mount: Mount, home_after: bool = True) -> None:
        """Simulate tip drop.
        
        Args:
            mount: Mount to drop tip from
            home_after: Whether to home after dropping (ignored)
        """
        mount_name = "left" if mount == Mount.LEFT else "right"
        logger.info(f"Dropping tip from {mount_name} mount")
        
        success = await self._simulation_client.drop_tip(mount_name)
        if not success:
            raise RuntimeError(f"Failed to drop tip from {mount_name} mount")
    
    # Liquid handling
    
    async def aspirate(self, mount: Mount, volume: float, speed: float) -> None:
        """Simulate liquid aspiration.
        
        Args:
            mount: Mount to aspirate with
            volume: Volume in microliters
            speed: Aspiration speed
        """
        mount_name = "left" if mount == Mount.LEFT else "right"
        logger.info(f"Aspirating {volume}μL on {mount_name} mount")
        
        success = await self._simulation_client.aspirate(mount_name, volume)
        if not success:
            raise RuntimeError(f"Failed to aspirate on {mount_name} mount")
    
    async def dispense(self, mount: Mount, volume: float, speed: float) -> None:
        """Simulate liquid dispensing.
        
        Args:
            mount: Mount to dispense with  
            volume: Volume in microliters
            speed: Dispense speed
        """
        mount_name = "left" if mount == Mount.LEFT else "right"
        logger.info(f"Dispensing {volume}μL on {mount_name} mount")
        
        success = await self._simulation_client.dispense(mount_name, volume)
        if not success:
            raise RuntimeError(f"Failed to dispense on {mount_name} mount")
    
    # Hardware state and control
    
    def set_lights(self, button: Optional[bool] = None, rails: Optional[bool] = None) -> None:
        """Set robot lights state.
        
        Args:
            button: Button light state
            rails: Rail lights state
        """
        if rails is not None:
            self._lights_on = rails
        logger.debug(f"Lights set: button={button}, rails={rails}")
    
    def get_lights(self) -> Dict[str, bool]:
        """Get current lights state."""
        return {"rails": self._lights_on, "button": False}
    
    @property
    def board_revision(self) -> BoardRevision:
        """Get board revision (simulated)."""
        return BoardRevision.OG
    
    @property
    def fw_version(self) -> Optional[str]:
        """Get firmware version (simulated)."""
        return "simulation-1.0.0"
    
    # Status and diagnostics
    
    async def get_attached_instruments(
        self, expected: Dict[Mount, "PipetteName"]
    ) -> "AttachedInstruments":
        """Get attached instruments info (simulated)."""
        # Return empty/default instruments for simulation
        from ..dev_types import AttachedInstruments, AttachedPipette
        
        return {
            Mount.LEFT: AttachedPipette(),
            Mount.RIGHT: AttachedPipette(),
        }
    
    async def get_instrument_max_height(
        self, mount: Mount, critical_point: Optional[str] = None
    ) -> float:
        """Get max height for instrument (simulated)."""
        return 218.0  # Max Z height in mm
    
    def door_state(self) -> DoorState:
        """Get door state (simulated)."""
        return self._door_state
    
    def estop_status(self) -> EstopState:
        """Get emergency stop status (simulated)."""  
        return self._estop_state
    
    async def get_status_bar_state(self) -> StatusBarState:
        """Get status bar state (simulated)."""
        return StatusBarState.IDLE
    
    # Compatibility methods for Controller interface
    
    async def update_position(self) -> None:
        """Update position from hardware (no-op in simulation)."""
        pass
    
    async def refresh_positions(self) -> None:
        """Refresh positions (no-op in simulation)."""
        pass
    
    def pause(self) -> None:
        """Pause robot (no-op in simulation)."""
        pass
    
    def resume(self) -> None:
        """Resume robot (no-op in simulation)."""
        pass
    
    async def halt(self) -> None:
        """Halt robot (no-op in simulation)."""
        pass
    
    async def watch(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Watch for hardware events (no-op in simulation)."""
        pass
    
    def start_gpio_door_watcher(self, loop: asyncio.AbstractEventLoop, update_door_state: Any) -> None:
        """Start GPIO door watcher (no-op in simulation)."""
        pass
    
    @property
    def module_controls(self):
        """Module controls property."""
        return getattr(self, '_module_controls', None)
    
    @module_controls.setter
    def module_controls(self, value):
        """Set module controls."""
        self._module_controls = value
    
    async def hard_halt(self) -> None:
        """Hard halt robot (compatibility method for simulation)."""
        # In simulation, we can just halt normally
        await self.halt()
    
    async def clean_up(self) -> None:
        """Clean up simulation controller."""
        await self.disconnect()