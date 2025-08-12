from pathlib import Path

from zmq_robot_server import ZMQ_Robot_Server


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../assets").resolve())

class ZMQ_PF400_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot with integrated control"""

    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        super().__init__(simulation_app, robot, robot_name, port, motion_type)

        # Initialize PF400-specific motion generation
        self._initialize_motion_generation()

    def handle_command(self, request):
        """Handle incoming ZMQ command"""
        # Try to handle with core robot commands first
        response = self.handle_core_robot_commands(request)
        if response is not None:
            return response

        # Handle PF400-specific commands here if needed
        action = request.get("action", "")
        return self.create_error_response(f"Unknown action: {action}")

    def _initialize_motion_generation(self):
        """Initialize motion generation algorithms for the PF400"""
        # PF400 robot configuration paths
        robot_config_dir = CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/pf400"
        robot_description_path = robot_config_dir + "/pf400_descriptor.yaml"
        urdf_path = robot_config_dir + "/pf400.urdf"

        # Use superclass method
        self.initialize_motion_generation(robot_description_path, urdf_path, 'pointer')
