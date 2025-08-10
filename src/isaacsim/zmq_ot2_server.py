from zmq_robot_server import ZMQ_Robot_Server

class ZMQ_OT2_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for OT-2 robot with opentrons-specific commands"""
    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        super().__init__(simulation_app, robot, robot_name, port, motion_type)

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

    def is_virtual_joint(self, joint_name: str) -> bool:
        """Check if a joint is virtual (simulated but not physically controlled)"""
        return joint_name in self.virtual_joints

    def is_physical_joint(self, joint_name: str) -> bool:
        """Check if a joint is physical (controlled in Isaac Sim)"""
        return joint_name in self.joint_names

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
        """Move a single joint to target position (physical or virtual)"""
        if not (self.is_physical_joint(joint_name) or self.is_virtual_joint(joint_name)):
            return self.create_error_response(f"Unknown joint: {joint_name}")

        # Check limits
        min_pos, max_pos = self.joint_limits[joint_name]
        if target_position < min_pos or target_position > max_pos:
            return self.create_error_response(f"Target position {target_position} out of bounds for {joint_name} [{min_pos}, {max_pos}]")

        try:
            # Handle virtual joints (soft simulation)
            if self.is_virtual_joint(joint_name):
                self.virtual_joints[joint_name] = target_position
                print(f"Virtual joint {joint_name} moved to {target_position} (soft simulation)")
                return self.create_success_response(
                    f"Virtual joint {joint_name} moved to {target_position}m (soft simulation)",
                    joint=joint_name,
                    target_position=target_position,
                    virtual=True
                )

            # Handle physical joints (Isaac Sim control)
            current_positions = self.robot.get_joint_positions()
            joint_index = self.joint_names.index(joint_name)

            # Update the specific joint
            new_positions = current_positions.copy()
            new_positions[joint_index] = target_position

            # Apply to robot
            self.robot.set_joint_positions(new_positions)

            return self.create_success_response(
                f"Physical joint {joint_name} moved to {target_position}m",
                joint=joint_name,
                target_position=target_position,
                virtual=False
            )
        except Exception as e:
            return self.create_error_response(f"Failed to move joint: {str(e)}")

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

            # Handle physical joints
            if physical_commands:
                self.robot.set_joint_positions(new_positions)

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

    def get_robot_status(self):
        """Get robot status information"""
        return {
            "status": "success",
            "robot_status": {
                "is_moving": False,  # Could track this in future
                "ready": True,
                "physical_joint_count": len(self.joint_names),
                "virtual_joint_count": len(self.virtual_joints),
                "total_joint_count": len(self.joint_names) + len(self.virtual_joints),
                "left_tip_attached": self.left_tip_attached,
                "right_tip_attached": self.right_tip_attached,
            }
        }

    def home_robot(self):
        """Return all joints (physical and virtual) to home positions"""
        try:
            home_commands = []
            for joint_name, home_pos in self.home_positions.items():
                home_commands.append({
                    "joint": joint_name,
                    "target_position": home_pos
                })

            print("Homing robot (physical and virtual joints)...")
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
        """Simulate tip drop using virtual ejector"""
        print(f"Simulating tip drop on {mount} mount using virtual ejector")

        try:
            if mount == "left":
                # Extend virtual ejector to push tip off (soft simulation)
                self.move_single_joint("left_tip_ejector_joint", 0.005)
                # Retract virtual ejector
                self.move_single_joint("left_tip_ejector_joint", 0.0)
                self.left_tip_attached = False
                print("Left tip ejected (soft simulation)")
            elif mount == "right":
                self.move_single_joint("right_tip_ejector_joint", 0.005)
                self.move_single_joint("right_tip_ejector_joint", 0.0)
                self.right_tip_attached = False
                print("Right tip ejected (soft simulation)")
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

            return {
                "status": "success",
                "message": f"Tip drop on {mount} mount (virtual ejector)",
                "mount": mount,
                "virtual_ejector": True
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to drop tip: {str(e)}"}

    def aspirate(self, mount: str, volume: float):
        """Simulate liquid aspiration using virtual plunger"""
        print(f"Simulating aspirate {volume}μL on {mount} mount using virtual plunger")

        try:
            # Convert volume to plunger position (simplified linear mapping)
            plunger_position = min(volume / 1000.0 * 0.019, 0.019)  # Max 19mm

            if mount == "left":
                result = self.move_single_joint("left_plunger_joint", plunger_position)
                print(f"Virtual left plunger moved to {plunger_position:.4f}m for {volume}μL")
                return result
            elif mount == "right":
                result = self.move_single_joint("right_plunger_joint", plunger_position)
                print(f"Virtual right plunger moved to {plunger_position:.4f}m for {volume}μL")
                return result
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

        except Exception as e:
            return {"status": "error", "message": f"Failed to aspirate: {str(e)}"}

    def dispense(self, mount: str, volume: float):
        """Simulate liquid dispensing using virtual plunger"""
        print(f"Simulating dispense {volume}μL on {mount} mount using virtual plunger")

        try:
            # Return plunger to home position for full dispense
            if mount == "left":
                result = self.move_single_joint("left_plunger_joint", 0.0)
                print(f"Virtual left plunger returned to home (0.0m) for {volume}μL dispense")
                return result
            elif mount == "right":
                result = self.move_single_joint("right_plunger_joint", 0.0)
                print(f"Virtual right plunger returned to home (0.0m) for {volume}μL dispense")
                return result
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

        except Exception as e:
            return {"status": "error", "message": f"Failed to dispense: {str(e)}"}
