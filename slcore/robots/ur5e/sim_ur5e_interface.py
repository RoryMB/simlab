from typing import Optional

from madsci.client.event_client import EventClient
from ur_interface.ur_kinematics import get_pose_from_joint_angles

from slcore.robots.common.zmq_client_base import ZMQClientInterface


class SimUR5e(ZMQClientInterface):
    """Main Driver Class for the UR5e Robot Arm."""

    device_number: int = 0

    def __init__(
        self,
        device_number: int = 0,
        zmq_server_url: str = "tcp://localhost:5555",
        logger: Optional[EventClient] = None,
        robot_model: str = "UR5e"
    ) -> "SimUR5e":
        """Initialize the robot ZMQ client."""
        super().__init__(zmq_server_url, logger)
        self.device_number = device_number
        self.robot_model = robot_model

        # Validate robot model
        if robot_model.lower() != "ur5e":
            raise ValueError(f"Unsupported robot model: {robot_model}. Only UR5e is supported.")

        self.logger.log(f"Robot model: {self.robot_model}")

    def run_command(self, command: str) -> None:
        """Run a command on the robot."""
        self.logger.log(f"Running command {command} on device number {self.device_number}.")

        # Example of sending a generic command via ZMQ
        zmq_command = {"action": "run_command", "command": command, "device_number": self.device_number}
        response = self.send_zmq_command(zmq_command)

        if response.get("status") != "success":
            self.logger.log(f"Command failed: {response.get('message', 'Unknown error')}")

    def move_to_location(self, joint_angles: list) -> bool:
        """Move robot to specified location coordinates."""
        self.logger.log(f"Moving to joint_angles: {joint_angles}")

        try:
            # Send move command via ZMQ
            zmq_command = {"action": "move_joints", "joint_angles": joint_angles}
            response = self.send_zmq_command(zmq_command)

            success = response.get("status") == "success"
            if success:
                self.logger.log(f"Successfully moved to joint_angles {joint_angles}")
            else:
                self.logger.log(f"Failed to move to joint_angles: {response.get('message', 'Unknown error')}")

            return success

        except Exception as e:
            self.logger.log(f"Error processing joint_angles {joint_angles}: {e}")
            return False

    def getj(self) -> list:
        """Get current robot joint positions."""
        zmq_command = {"action": "get_joints"}
        response = self.send_zmq_command(zmq_command)

        if response.get("status") == "success":
            return response.get("joint_angles", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            self.logger.log(f"Failed to get position: {response.get('message', 'Unknown error')}")
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def get_pose_from_joints(self) -> list:
        """Get current end-effector pose from joint positions."""
        joints = self.getj()
        return get_pose_from_joint_angles(joints, "UR5e")

    def set_freedrive(self, timeout: int = 60) -> bool:
        """Enable freedrive mode via ZMQ"""
        zmq_command = {"action": "set_freedrive", "timeout": timeout}
        response = self.send_zmq_command(zmq_command)
        success = response.get("status") == "success"
        if success:
            self.logger.log(f"Freedrive enabled for {timeout} seconds")
        else:
            self.logger.log(f"Failed to enable freedrive: {response.get('message', 'Unknown error')}")
        return success

    def open_gripper(self) -> bool:
        """Open gripper via ZMQ"""
        zmq_command = {"action": "gripper_open"}
        response = self.send_zmq_command(zmq_command)
        success = response.get("status") == "success"
        if success:
            self.logger.log("Gripper opened successfully")
        else:
            self.logger.log(f"Failed to open gripper: {response.get('message', 'Unknown error')}")
        return success

    def close_gripper(self) -> bool:
        """Close gripper via ZMQ"""
        zmq_command = {"action": "gripper_close"}
        response = self.send_zmq_command(zmq_command)
        success = response.get("status") == "success"
        if success:
            self.logger.log("Gripper closed successfully")
        else:
            self.logger.log(f"Failed to close gripper: {response.get('message', 'Unknown error')}")
        return success
