from zmq_robot_server import ZMQ_Robot_Server

class ZMQ_OT2_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for OT-2 robot with opentrons-specific commands"""
    def __init__(self, simulation_app, robot, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_name, port)
        
        # OT2-specific motion state (since OT2 manages its own motion)
        self.is_moving = False
        self.motion_complete = False

        # OT-2 joint mapping (joint index -> joint name)
        # Primary movement joints (required for visual robot motion)
        self.joint_names = [
            "pipette_rail_joint",      # 0: Y-axis (front/back)
            "pipette_casing_joint",    # 1: X-axis (left/right)
            "pipette_left_joint",      # 2: Left Z (up/down)
            "pipette_right_joint",     # 3: Right Z (up/down)
            # TODO: Add these when implementing fluid dynamics and physical tip handling
            # "left_plunger_joint",      # 4: Left plunger
            # "right_plunger_joint",     # 5: Right plunger
            # "left_tip_ejector_joint",  # 6: Left tip ejector
            # "right_tip_ejector_joint", # 7: Right tip ejector
        ]

        # Virtual joints (simulated but not physically controlled)
        self.virtual_joints = {
            "left_plunger_joint": 0.0,
            "right_plunger_joint": 0.0,
            "left_tip_ejector_joint": 0.0,
            "right_tip_ejector_joint": 0.0,
        }

        # Joint limits (from test_ot2_server.py)
        self.joint_limits = {
            # Physical joints (controlled in Isaac Sim)
            "pipette_rail_joint": (0.0, 0.353),
            "pipette_casing_joint": (0.0, 0.418),
            "pipette_left_joint": (-0.218, 0.0),
            "pipette_right_joint": (-0.218, 0.0),
            # Virtual joints (soft simulation only)
            "left_plunger_joint": (0.0, 0.019),
            "right_plunger_joint": (0.0, 0.019),
            "left_tip_ejector_joint": (0.0, 0.005),
            "right_tip_ejector_joint": (0.0, 0.005),
        }

        # Home positions
        self.home_positions = {
            # Physical joint homes
            "pipette_rail_joint": 0.353,      # Y-axis home (back)
            "pipette_casing_joint": 0.418,    # X-axis home (right)
            "pipette_left_joint": 0.0,        # Left Z home (top)
            "pipette_right_joint": 0.0,       # Right Z home (top)
            # Virtual joint homes (soft simulation)
            "left_plunger_joint": 0.0,        # Left plunger home
            "right_plunger_joint": 0.0,       # Right plunger home
            "left_tip_ejector_joint": 0.0,    # Left tip ejector retracted
            "right_tip_ejector_joint": 0.0,   # Right tip ejector retracted
        }

        # Tip attachment state
        self.left_tip_attached = False
        self.right_tip_attached = False

        # Light states
        self.button_light = False
        self.rail_lights = False

        # Robot state
        self.is_paused = False

    def is_virtual_joint(self, joint_name: str) -> bool:
        """Check if a joint is virtual (simulated but not physically controlled)"""
        return joint_name in self.virtual_joints

    def is_physical_joint(self, joint_name: str) -> bool:
        """Check if a joint is physical (controlled in Isaac Sim)"""
        return joint_name in self.joint_names

    def handle_command(self, request):
        """Handle incoming ZMQ command from opentrons package"""
        action = request.get("action", "")

        # DEBUG: Log all incoming requests
        print(f"[ZMQ_OT2_SERVER] RECEIVED REQUEST: {request}")
        print(f"[ZMQ_OT2_SERVER] ACTION: {action}")

        if action == "move_joints":
            joint_commands = request.get("joint_commands", [])

            if joint_commands:
                return self.move_multiple_joints(joint_commands)
            else:
                return {"status": "error", "message": "No joint commands provided"}

        elif action == "get_joints":
            return self.get_joint_positions()

        elif action == "home":
            return self.home_robot()

        elif action == "is_homed":
            axes = request.get("axes", [])
            return self.check_homed_status(axes)

        elif action == "probe":
            axis = request.get("axis")
            distance = request.get("distance", 0.0)
            return self.probe_axis(axis, distance)

        elif action == "get_attached_instruments":
            return self.get_attached_instruments()

        elif action == "set_button_light":
            state = request.get("state", False)
            return self.set_button_light(state)

        elif action == "set_rail_lights":
            state = request.get("state", False)
            return self.set_rail_lights(state)

        elif action == "get_lights":
            return self.get_lights()

        elif action == "pause":
            return self.pause_robot()

        elif action == "resume":
            return self.resume_robot()

        elif action == "halt":
            return self.halt_robot()

        else:
            error_response = self.create_error_response(f"Unknown action: {action}")
            print(f"[ZMQ_OT2_SERVER] UNKNOWN ACTION RESPONSE: {error_response}")
            return error_response

    def move_multiple_joints(self, joint_commands):
        """Move multiple joints simultaneously (physical and virtual)"""
        try:
            current_positions = self.robot.get_joint_positions()
            new_positions = current_positions.copy()
            virtual_commands = []
            physical_commands = []

            # Validate and separate commands
            for cmd in joint_commands:
                joint_name = cmd.get("joint")
                target_position = cmd.get("target_position")

                if not (self.is_physical_joint(joint_name) or self.is_virtual_joint(joint_name)):
                    return {"status": "error", "message": f"Unknown joint: {joint_name}"}

                min_pos, max_pos = self.joint_limits[joint_name]
                if target_position < min_pos or target_position > max_pos:
                    return {"status": "error", "message": f"Target position {target_position} out of bounds for {joint_name}"}

                if self.is_virtual_joint(joint_name):
                    virtual_commands.append(cmd)
                else:
                    physical_commands.append(cmd)
                    joint_index = self.joint_names.index(joint_name)
                    new_positions[joint_index] = target_position

            # Handle virtual joints
            for cmd in virtual_commands:
                joint_name = cmd.get("joint")
                target_position = cmd.get("target_position")
                self.virtual_joints[joint_name] = target_position
                print(f"Virtual joint {joint_name} moved to {target_position} (soft simulation)")

            # Handle physical joints using base class motion execution system
            if physical_commands:
                self.current_action = "move_joints"
                self.target_joints = new_positions
                self.is_moving = True
                self.motion_complete = False
                print(f"Physical joints motion queued (motion_type={self.motion_type})")

            return {
                "status": "success",
                "message": f"Moving {len(joint_commands)} joints ({len(physical_commands)} physical, {len(virtual_commands)} virtual)",
                "joint_commands": joint_commands,
                "physical_joints": len(physical_commands),
                "virtual_joints": len(virtual_commands)
            }

        except Exception as e:
            return {"status": "error", "message": f"Failed to move joints: {str(e)}"}

    def get_joint_positions(self):
        """Get current joint positions (physical and virtual)"""
        try:
            joint_positions = {}

            # Get physical joint positions
            positions = self.robot.get_joint_positions()
            for i, joint_name in enumerate(self.joint_names):
                joint_positions[joint_name] = positions[i] if i < len(positions) else 0.0

            # Add virtual joint positions
            for joint_name, position in self.virtual_joints.items():
                joint_positions[joint_name] = position

            return {"status": "success", "joint_positions": joint_positions}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

    def home_robot(self):
        """Return all joints (physical and virtual) to home positions"""
        print(f"[ZMQ_OT2_SERVER] HOME_ROBOT: Starting home sequence")
        try:
            home_commands = []
            for joint_name, home_pos in self.home_positions.items():
                home_commands.append({
                    "joint": joint_name,
                    "target_position": home_pos
                })

            print(f"[ZMQ_OT2_SERVER] HOME_COMMANDS: {home_commands}")
            print("Homing robot (physical and virtual joints)...")
            result = self.move_multiple_joints(home_commands)
            print(f"[ZMQ_OT2_SERVER] HOME_RESULT: {result}")
            return result

        except Exception as e:
            return {"status": "error", "message": f"Failed to home robot: {str(e)}"}

    def check_homed_status(self, axes):
        """Check if specified axes are homed"""
        try:
            if not axes:
                return {"status": "error", "message": "No axes specified"}

            # Validate that all axes exist
            for axis in axes:
                if not (self.is_physical_joint(axis) or self.is_virtual_joint(axis)):
                    return {"status": "error", "message": f"Unknown axis: {axis}"}

            # Get current positions
            current_positions = self.get_joint_positions()
            if current_positions.get("status") != "success":
                return {"status": "error", "message": "Failed to get current positions"}

            joint_positions = current_positions["joint_positions"]

            # Check each axis against home position (tolerance: 0.001m = 1mm)
            tolerance = 0.001
            all_homed = True
            homed_status = {}

            for axis in axes:
                current_pos = joint_positions.get(axis, 0.0)
                home_pos = self.home_positions.get(axis, 0.0)
                axis_homed = abs(current_pos - home_pos) <= tolerance
                homed_status[axis] = axis_homed
                if not axis_homed:
                    all_homed = False

            print(f"Homed status for {axes}: {homed_status} (tolerance: {tolerance}m)")
            return {
                "status": "success",
                "homed": all_homed,
                "axes": axes,
                "individual_status": homed_status
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to check homed status: {str(e)}"}

    def probe_axis(self, axis, distance):
        """Run a probe on specified axis"""
        try:
            if not axis:
                return {"status": "error", "message": "No axis specified"}

            if not (self.is_physical_joint(axis) or self.is_virtual_joint(axis)):
                return {"status": "error", "message": f"Unknown axis: {axis}"}

            print(f"Probing axis {axis} for distance {distance}")

            # Get current position
            current_positions = self.get_joint_positions()
            if current_positions.get("status") != "success":
                return {"status": "error", "message": "Failed to get current positions"}

            current_pos = current_positions["joint_positions"].get(axis, 0.0)

            # Calculate target position and check limits
            target_pos = current_pos + distance
            min_pos, max_pos = self.joint_limits[axis]

            # Clamp to joint limits (probe stops at limits)
            actual_target = max(min_pos, min(max_pos, target_pos))
            actual_distance = actual_target - current_pos

            # Actually move the axis to probe
            move_command = [{
                "joint": axis,
                "target_position": actual_target
            }]

            move_result = self.move_multiple_joints(move_command)
            if move_result.get("status") != "success":
                return {"status": "error", "message": f"Failed to move axis during probe: {move_result.get('message')}"}

            # Get final position after movement
            final_positions = self.get_joint_positions()
            if final_positions.get("status") != "success":
                return {"status": "error", "message": "Failed to get final position after probe"}

            final_pos = final_positions["joint_positions"].get(axis, current_pos)

            print(f"Probe moved {axis} from {current_pos:.4f} to {final_pos:.4f} (distance: {actual_distance:.4f})")

            return {
                "status": "success",
                "position": {axis: final_pos},
                "distance_traveled": actual_distance,
                "hit_limit": abs(actual_distance) < abs(distance)
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to probe axis: {str(e)}"}

    def get_attached_instruments(self):
        """Get attached instruments from simulation"""
        try:
            # Return default simulation instrument configuration
            instruments = {
                "left": {
                    "model": "p300_single_v2.1",
                    "tip_attached": self.left_tip_attached,
                },
                "right": {
                    "model": "p300_single_v2.1",
                    "tip_attached": self.right_tip_attached,
                }
            }

            print(f"Attached instruments: {instruments}")
            return {
                "status": "success",
                "instruments": instruments
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to get attached instruments: {str(e)}"}

    def set_button_light(self, state):
        """Set button light state"""
        try:
            self.button_light = bool(state)
            print(f"Button light set to: {self.button_light}")
            return {
                "status": "success",
                "button_light": self.button_light
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to set button light: {str(e)}"}

    def set_rail_lights(self, state):
        """Set rail lights state"""
        try:
            self.rail_lights = bool(state)
            print(f"Rail lights set to: {self.rail_lights}")
            return {
                "status": "success",
                "rail_lights": self.rail_lights
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to set rail lights: {str(e)}"}

    def get_lights(self):
        """Get current light states"""
        try:
            lights = {
                "button": self.button_light,
                "rails": self.rail_lights
            }
            print(f"Current lights: {lights}")
            return {
                "status": "success",
                "lights": lights
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to get lights: {str(e)}"}

    def pause_robot(self):
        """Pause current robot movement"""
        try:
            self.is_paused = True
            print("Robot movement paused")
            return {
                "status": "success",
                "message": "Robot paused",
                "paused": True,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to pause robot: {str(e)}"}

    def resume_robot(self):
        """Resume paused robot movement"""
        try:
            self.is_paused = False
            print("Robot movement resumed")
            return {
                "status": "success",
                "message": "Robot resumed",
                "paused": False,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to resume robot: {str(e)}"}

    def halt_robot(self):
        """Stop current robot movement immediately"""
        try:
            # Immediately stop all motion
            self.is_moving = False
            self.motion_complete = True
            self.is_paused = False
            self.current_action = None
            self.target_joints = None

            print("Robot movement halted immediately")
            return {
                "status": "success",
                "message": "Robot halted",
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to halt robot: {str(e)}"}
    
    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.is_paused:
            return

        if self.current_action is None:
            return

        if self.current_action == "move_joints":
            self.execute_move_joints()
