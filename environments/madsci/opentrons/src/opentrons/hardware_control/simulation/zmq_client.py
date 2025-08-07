"""
ZMQ client for communicating with external physics simulation.
"""

import json
import logging
import os
import asyncio
from typing import Dict, List, Optional, Any
import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)


class ZMQSimulationClient:
    """Client for communicating with ZMQ-based physics simulation."""
    
    def __init__(self, server_url: Optional[str] = None):
        """Initialize ZMQ client.
        
        Args:
            server_url: URL of simulation server. If None, uses environment variable
                       OT2_SIMULATION_SERVER or defaults to tcp://localhost:5556
        """
        self.server_url = (
            server_url or 
            os.environ.get("OT2_SIMULATION_SERVER", "tcp://localhost:5556")
        )
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        self._connected = False
        
    async def connect(self) -> None:
        """Connect to the simulation server."""
        if self._connected:
            return
            
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.server_url)
        self._connected = True
        
        logger.info(f"Connected to OT-2 simulation server at {self.server_url}")
        
    async def disconnect(self) -> None:
        """Disconnect from the simulation server."""
        if not self._connected:
            return
            
        if self.socket:
            self.socket.close()
            self.socket = None
            
        if self.context:
            self.context.term()
            self.context = None
            
        self._connected = False
        logger.info("Disconnected from OT-2 simulation server")
        
    async def _send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to the simulation server and get response.
        
        Args:
            command: Command dictionary to send
            
        Returns:
            Response dictionary from server
            
        Raises:
            RuntimeError: If not connected or communication fails
        """
        if not self._connected or not self.socket:
            raise RuntimeError("Not connected to simulation server")
            
        try:
            # Send command
            message = json.dumps(command)
            await self.socket.send_string(message)
            
            # Wait for response with timeout
            response_str = await asyncio.wait_for(
                self.socket.recv_string(), 
                timeout=10.0
            )
            response = json.loads(response_str)
            
            logger.debug(f"Sent: {command}, Received: {response}")
            
            return response
            
        except asyncio.TimeoutError:
            raise RuntimeError("Simulation server response timeout")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from server: {e}")
        except Exception as e:
            raise RuntimeError(f"Communication error: {e}")
    
    async def move_joint(self, joint_name: str, target_position: float) -> bool:
        """Move a single joint to target position.
        
        Args:
            joint_name: Name of joint to move
            target_position: Target position in meters
            
        Returns:
            True if successful
        """
        command = {
            "action": "move_joint",
            "joint": joint_name,
            "target_position": target_position
        }
        
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def move_joints(self, joint_commands: List[Dict[str, Any]]) -> bool:
        """Move multiple joints simultaneously.
        
        Args:
            joint_commands: List of joint command dictionaries
            
        Returns:
            True if successful
        """
        command = {
            "action": "move_joints",
            "joint_commands": joint_commands
        }
        
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def get_joint_positions(self) -> Dict[str, float]:
        """Get current joint positions.
        
        Returns:
            Dictionary mapping joint names to positions in meters
        """
        command = {"action": "get_joints"}
        response = await self._send_command(command)
        
        if response.get("status") == "success":
            return response.get("joint_positions", {})
        else:
            raise RuntimeError(f"Failed to get joint positions: {response}")
    
    async def home_robot(self) -> bool:
        """Home all robot joints.
        
        Returns:
            True if successful
        """
        command = {"action": "home"}
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def pick_up_tip(self, mount: str) -> bool:
        """Simulate tip pickup.
        
        Args:
            mount: Mount name ("left" or "right")
            
        Returns:
            True if successful
        """
        command = {
            "action": "pick_up_tip",
            "mount": mount
        }
        
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def drop_tip(self, mount: str) -> bool:
        """Simulate tip drop.
        
        Args:
            mount: Mount name ("left" or "right")
            
        Returns:
            True if successful
        """
        command = {
            "action": "drop_tip", 
            "mount": mount
        }
        
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def aspirate(self, mount: str, volume: float) -> bool:
        """Simulate liquid aspiration.
        
        Args:
            mount: Mount name ("left" or "right")
            volume: Volume in microliters
            
        Returns:
            True if successful
        """
        command = {
            "action": "aspirate",
            "mount": mount,
            "volume": volume
        }
        
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def dispense(self, mount: str, volume: float) -> bool:
        """Simulate liquid dispensing.
        
        Args:
            mount: Mount name ("left" or "right")  
            volume: Volume in microliters
            
        Returns:
            True if successful
        """
        command = {
            "action": "dispense",
            "mount": mount,
            "volume": volume
        }
        
        response = await self._send_command(command)
        return response.get("status") == "success"
    
    async def get_status(self) -> Dict[str, Any]:
        """Get simulation robot status.
        
        Returns:
            Status dictionary
        """
        command = {"action": "get_status"}
        response = await self._send_command(command)
        
        if response.get("status") == "success":
            return response.get("robot_status", {})
        else:
            raise RuntimeError(f"Failed to get status: {response}")