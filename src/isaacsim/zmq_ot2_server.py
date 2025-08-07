from zmq_robot_server import ZMQ_Robot_Server

class ZMQ_OT2_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for OT-2 robot with opentrons-specific commands"""
    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        super().__init__(simulation_app, robot, robot_name, port, motion_type)

        # OT-2 joint mapping (joint index -> joint name)
        self.joint_names = [
            "pipette_rail_joint",      # 0: Y-axis (front/back)
            "pipette_casing_joint",    # 1: X-axis (left/right)
            "pipette_left_joint",      # 2: Left Z (up/down)
            "pipette_right_joint",     # 3: Right Z (up/down)
            "left_plunger_joint",      # 4: Left plunger
            "right_plunger_joint",     # 5: Right plunger
            "left_tip_ejector_joint",  # 6: Left tip ejector
            "right_tip_ejector_joint", # 7: Right tip ejector
        ]

        # Joint limits (from test_ot2_server.py)
        self.joint_limits = {
            "pipette_rail_joint": (0.0, 0.353),
            "pipette_casing_joint": (0.0, 0.418),
            "pipette_left_joint": (-0.218, 0.0),
            "pipette_right_joint": (-0.218, 0.0),
            "left_plunger_joint": (0.0, 0.019),
            "right_plunger_joint": (0.0, 0.019),
            "left_tip_ejector_joint": (0.0, 0.005),
            "right_tip_ejector_joint": (0.0, 0.005),
        }

        # Home positions
        self.home_positions = {
            "pipette_rail_joint": 0.353,      # Y-axis home (back)
            "pipette_casing_joint": 0.418,    # X-axis home (right)
            "pipette_left_joint": 0.0,        # Left Z home (top)
            "pipette_right_joint": 0.0,       # Right Z home (top)
            "left_plunger_joint": 0.0,        # Left plunger home
            "right_plunger_joint": 0.0,       # Right plunger home
            "left_tip_ejector_joint": 0.0,    # Left tip ejector retracted
            "right_tip_ejector_joint": 0.0,   # Right tip ejector retracted
        }

        # Tip attachment state
        self.left_tip_attached = False
        self.right_tip_attached = False

    def handle_command(self, request):
        """Handle incoming ZMQ command from opentrons package"""
        action = request.get("action", "")

        if action == "move_joint":
            joint_name = request.get("joint")
            target_position = request.get("target_position")

            if joint_name and target_position is not None:
                return self.move_single_joint(joint_name, target_position)
            else:
                return {"status": "error", "message": "Missing joint name or target position"}

        elif action == "move_joints":
            joint_commands = request.get("joint_commands", [])

            if joint_commands:
                return self.move_multiple_joints(joint_commands)
            else:
                return {"status": "error", "message": "No joint commands provided"}

        elif action == "get_joints":
            return self.get_joint_positions()

        elif action == "get_status":
            return self.get_robot_status()

        elif action == "home":
            return self.home_robot()

        elif action == "pick_up_tip":
            mount = request.get("mount", "left")
            return self.pick_up_tip(mount)

        elif action == "drop_tip":
            mount = request.get("mount", "left")
            return self.drop_tip(mount)

        elif action == "aspirate":
            mount = request.get("mount", "left")
            volume = request.get("volume", 0.0)
            return self.aspirate(mount, volume)

        elif action == "dispense":
            mount = request.get("mount", "left")
            volume = request.get("volume", 0.0)
            return self.dispense(mount, volume)

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def move_single_joint(self, joint_name: str, target_position: float):
        """Move a single joint to target position"""
        if joint_name not in self.joint_names:
            return self.create_error_response(f"Unknown joint: {joint_name}")

        # Check limits
        min_pos, max_pos = self.joint_limits[joint_name]
        if target_position < min_pos or target_position > max_pos:
            return self.create_error_response(f"Target position {target_position} out of bounds for {joint_name} [{min_pos}, {max_pos}]")

        try:
            # Get current joint positions
            current_positions = self.robot.get_joint_positions()
            joint_index = self.joint_names.index(joint_name)

            # Update the specific joint
            new_positions = current_positions.copy()
            new_positions[joint_index] = target_position

            # Apply to robot
            self.robot.set_joint_positions(new_positions)

            return self.create_success_response(
                f"Moving {joint_name} to {target_position}m",
                joint=joint_name,
                target_position=target_position
            )
        except Exception as e:
            return self.create_error_response(f"Failed to move joint: {str(e)}")

    def move_multiple_joints(self, joint_commands):
        """Move multiple joints simultaneously"""
        try:
            current_positions = self.robot.get_joint_positions()
            new_positions = current_positions.copy()

            # Validate and prepare all commands
            for cmd in joint_commands:
                joint_name = cmd.get("joint")
                target_position = cmd.get("target_position")

                if joint_name not in self.joint_names:
                    return {"status": "error", "message": f"Unknown joint: {joint_name}"}

                min_pos, max_pos = self.joint_limits[joint_name]
                if target_position < min_pos or target_position > max_pos:
                    return {"status": "error", "message": f"Target position {target_position} out of bounds for {joint_name}"}

                joint_index = self.joint_names.index(joint_name)
                new_positions[joint_index] = target_position

            # Apply all movements
            self.robot.set_joint_positions(new_positions)

            return {
                "status": "success",
                "message": f"Moving {len(joint_commands)} joints",
                "joint_commands": joint_commands
            }

        except Exception as e:
            return {"status": "error", "message": f"Failed to move joints: {str(e)}"}

    def get_joint_positions(self):
        """Get current joint positions"""
        try:
            positions = self.robot.get_joint_positions()
            joint_positions = {}
            for i, joint_name in enumerate(self.joint_names):
                joint_positions[joint_name] = positions[i] if i < len(positions) else 0.0

            return {"status": "success", "joint_positions": joint_positions}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

    def get_robot_status(self):
        """Get robot status information"""
        return {
            "status": "success",
            "robot_status": {
                "is_moving": False,  # Could track this in future
                "ready": True,
                "joint_count": len(self.joint_names),
                "left_tip_attached": self.left_tip_attached,
                "right_tip_attached": self.right_tip_attached,
            }
        }

    def home_robot(self):
        """Return all joints to home positions"""
        try:
            home_commands = []
            for joint_name, home_pos in self.home_positions.items():
                home_commands.append({
                    "joint": joint_name,
                    "target_position": home_pos
                })

            return self.move_multiple_joints(home_commands)

        except Exception as e:
            return {"status": "error", "message": f"Failed to home robot: {str(e)}"}

    def pick_up_tip(self, mount: str):
        """Simulate tip pickup"""
        print(f"Simulating tip pickup on {mount} mount")

        if mount == "left":
            self.left_tip_attached = True
        elif mount == "right":
            self.right_tip_attached = True
        else:
            return {"status": "error", "message": f"Invalid mount: {mount}"}

        return {
            "status": "success",
            "message": f"Tip pickup on {mount} mount",
            "mount": mount
        }

    def drop_tip(self, mount: str):
        """Simulate tip drop using ejector"""
        print(f"Simulating tip drop on {mount} mount")

        try:
            if mount == "left":
                # Extend ejector to push tip off
                self.move_single_joint("left_tip_ejector_joint", 0.005)
                # Retract ejector
                self.move_single_joint("left_tip_ejector_joint", 0.0)
                self.left_tip_attached = False
            elif mount == "right":
                self.move_single_joint("right_tip_ejector_joint", 0.005)
                self.move_single_joint("right_tip_ejector_joint", 0.0)
                self.right_tip_attached = False
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

            return {
                "status": "success",
                "message": f"Tip drop on {mount} mount",
                "mount": mount
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to drop tip: {str(e)}"}

    def aspirate(self, mount: str, volume: float):
        """Simulate liquid aspiration"""
        print(f"Simulating aspirate {volume}μL on {mount} mount")

        try:
            # Convert volume to plunger position (simplified linear mapping)
            plunger_position = min(volume / 1000.0 * 0.019, 0.019)  # Max 19mm

            if mount == "left":
                return self.move_single_joint("left_plunger_joint", plunger_position)
            elif mount == "right":
                return self.move_single_joint("right_plunger_joint", plunger_position)
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

        except Exception as e:
            return {"status": "error", "message": f"Failed to aspirate: {str(e)}"}

    def dispense(self, mount: str, volume: float):
        """Simulate liquid dispensing"""
        print(f"Simulating dispense {volume}μL on {mount} mount")

        try:
            # Return plunger to home position for full dispense
            if mount == "left":
                return self.move_single_joint("left_plunger_joint", 0.0)
            elif mount == "right":
                return self.move_single_joint("right_plunger_joint", 0.0)
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

        except Exception as e:
            return {"status": "error", "message": f"Failed to dispense: {str(e)}"}
