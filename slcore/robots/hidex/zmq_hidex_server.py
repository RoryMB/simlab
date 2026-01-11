import numpy as np
from isaacsim.core.utils.types import ArticulationAction
from pxr import Gf

from slcore.robots.common.zmq_robot_server import ZMQ_Robot_Server
from slcore.robots.common.zmq_server_mixins import RaycastMixin

class ZMQ_Hidex_Server(RaycastMixin, ZMQ_Robot_Server):
    """Handles ZMQ communication for Hidex plate reader device"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, port)

        # Hidex drawer joint configuration
        self.drawer_open_position = 0.146
        self.drawer_closed_position = 0.0

        # Hidex raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, 1)  # Upward
        self.raycast_distance = 0.03  # 3cm reach

        # Track attached plate joint
        self._attached_plate = None

    def handle_command(self, request: dict) -> dict:
        """Handle incoming ZMQ command"""
        action = request.get("action", "")

        if action == "open":
            self.current_action = "open_drawer"
            self.target_joints = np.array([self.drawer_open_position])
            return self.create_success_response("open drawer queued")

        elif action == "close":
            self.current_action = "close_drawer_init"
            return self.create_success_response("close drawer queued")

        elif action == "run_assay":
            assay_name = request.get("assay_name")
            return self.execute_run_assay(assay_name)

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def execute_run_assay(self, assay_name):
        """Execute run_assay operation - check for plate presence"""

        if self._attached_plate:
            print(f"Robot {self.robot_name} run_assay operation (attached plate detected, assay_name={assay_name})")
            return self.create_success_response("run_assay operation completed", plate_detected=True, assay_name=assay_name)
        else:
            print(f"Robot {self.robot_name} run_assay operation failed (no plate detected)")
            return self.create_error_response("No plate detected in Hidex reader")

    def _attempt_attach_plate(self):
        """Try to attach a plate found at the pointer"""
        if self._attached_plate:
            return

        # Get raycast info
        try:
            world_position, world_direction = self._get_end_effector_raycast_info('pointer')

            # Perform raycast to detect plate
            hit_prim = self.raycast(world_position, world_direction, self.raycast_distance, self.robot_prim_path)

            if hit_prim:
                # Attach and store joint path
                self._attached_plate = self.attach_object(hit_prim.GetPath().pathString, 'pointer')
                print(f"Hidex attached object: {hit_prim.GetPath().pathString}")
        except Exception as e:
            print(f"Hidex failed to attach object: {e}")

    def _detach_plate(self):
        """Detach the currently attached plate"""
        if self._attached_plate:
            try:
                self.detach_object(self._attached_plate)
                self._attached_plate = None
                print("Hidex detached object")
            except Exception as e:
                print(f"Hidex failed to detach object: {e}")

    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.is_paused:
            return

        if self.current_action is None:
            return

        # Handle initialization of close action (on main thread)
        if self.current_action == "close_drawer_init":
            self._attempt_attach_plate()
            self.target_joints = np.array([self.drawer_closed_position])
            self.current_action = "close_drawer"

        action_type = self.current_action

        if action_type in ["open_drawer", "close_drawer"]:
            self.execute_move_joints()

            # Check if motion finished
            if self.current_action is None:
                # If we just finished opening, detach the plate so PF400 can pick it up
                if action_type == "open_drawer":
                    self._detach_plate()
