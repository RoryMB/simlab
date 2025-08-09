import numpy as np
from isaacsim.core.utils.types import ArticulationAction
from zmq_robot_server import ZMQ_Robot_Server

class ZMQ_PF400_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot with integrated control"""

    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        super().__init__(simulation_app, robot, robot_name, port, motion_type)

        # PF400 home position (safe position) - 7 joints to match robot
        self.home_position = [0.2, 0.0, 1.5708, 0.0, 0.0, 0.3, 0.0]  # 200mm Z, 90deg elbow, 300mm rail, gripper closed

        # Gripper state
        self.gripper_open = False

        # Integrated control state
        self.current_action = None  # Current action being executed
        self.target_joints = None   # Target joint positions
        self.is_moving = False      # Whether robot is currently moving
        self.collision_detected = False  # Collision flag
        self.motion_complete = False     # Motion completion flag
        self.collision_actors = None     # Actors involved in collision

    def handle_command(self, request):
        """Handle incoming ZMQ command - defer execution to update loop"""
        action = request.get("action", "")

        # Check for collisions
        if self.collision_detected:
            return self.create_error_response(f"Robot halted due to collision: {self.collision_actors}")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])

            if len(joint_angles) != 7:
                return self.create_error_response(f"Expected 7 joint angles, got {len(joint_angles)}")

            # Store command for execution in update loop (let Isaac Sim handle validation)
            self.current_action = "move_joints"
            self.target_joints = np.array(joint_angles)
            self.is_moving = True
            self.motion_complete = False

            return self.create_success_response("command queued", joint_angles=joint_angles)

        elif action == "get_joints":
            try:
                joint_positions = self.robot.get_joint_positions()
                return self.create_success_response("joints retrieved", joint_angles=joint_positions.tolist())
            except Exception as e:
                return self.create_error_response(f"Failed to get joint positions: {str(e)}")

        elif action == "home":
            # Store command for execution in update loop
            self.current_action = "move_joints"
            self.target_joints = np.array(self.home_position)
            self.is_moving = True
            self.motion_complete = False

            return self.create_success_response("homing queued", joint_angles=self.home_position)

        elif action == "gripper_open":
            try:
                self.gripper_open = True
                # Store command for execution in update loop
                self.current_action = "gripper_open"
                self.motion_complete = False
                return self.create_success_response("gripper open queued", gripper_state="open")
            except Exception as e:
                return self.create_error_response(f"Failed to queue gripper open: {str(e)}")

        elif action == "gripper_close":
            try:
                self.gripper_open = False
                # Store command for execution in update loop
                self.current_action = "gripper_close"
                self.motion_complete = False
                return self.create_success_response("gripper close queued", gripper_state="closed")
            except Exception as e:
                return self.create_error_response(f"Failed to queue gripper close: {str(e)}")

        elif action == "get_status":
            try:
                joint_positions = self.robot.get_joint_positions()
                return self.create_success_response(
                    "status retrieved",
                    joint_angles=joint_positions.tolist(),
                    gripper_state="open" if self.gripper_open else "closed",
                    is_homed=np.allclose(joint_positions, self.home_position, atol=0.01),
                    is_moving=self.is_moving,
                    collision_detected=self.collision_detected,
                    motion_complete=self.motion_complete,
                )
            except Exception as e:
                return self.create_error_response(f"Failed to get status: {str(e)}")

        else:
            return self.create_error_response(f"Unknown action: {action}")

    # Removed broken IK and validation functions - let Isaac Sim handle kinematics

    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.collision_detected:
            # Stop all motion if collision detected
            if self.is_moving:
                self.halt_motion()
            return

        if self.current_action is None:
            return

        try:
            if self.current_action == "move_joints":
                self._execute_move_joints()
            elif self.current_action == "gripper_open":
                self._execute_gripper_open()
            elif self.current_action == "gripper_close":
                self._execute_gripper_close()

        except Exception as e:
            print(f"Error executing action {self.current_action}: {e}")
            self.current_action = None
            self.is_moving = False

    def _execute_move_joints(self):
        """Execute joint movement in simulation"""
        if self.target_joints is None:
            return

        if self.motion_type == "teleport":
            # Teleport directly
            self.robot.set_joint_positions(self.target_joints)
            self.motion_complete = True
            self.is_moving = False
            self.current_action = None
        else:
            # Smooth motion
            action = ArticulationAction(joint_positions=self.target_joints)
            self.robot.apply_action(action)

            # Check if motion is complete
            current_joints = self.robot.get_joint_positions()
            diff = np.abs(current_joints - self.target_joints)
            max_diff = np.max(diff)

            velocities = self.robot.get_joint_velocities()
            max_vel = np.max(np.abs(velocities))

            # Motion is complete when close to target and low velocity
            if max_diff < 0.01 and max_vel < 0.008:
                self.motion_complete = True
                self.is_moving = False
                self.current_action = None
                print(f"Robot {self.robot_name} completed motion")

    def _execute_gripper_open(self):
        """Execute gripper opening"""
        current_joints = self.robot.get_joint_positions()
        current_joints[6] = 1.0  # Open gripper (7th joint)

        action = ArticulationAction(joint_positions=current_joints)
        self.robot.apply_action(action)

        self.motion_complete = True
        self.current_action = None
        print(f"Robot {self.robot_name} opened gripper")

    def _execute_gripper_close(self):
        """Execute gripper closing"""
        current_joints = self.robot.get_joint_positions()
        current_joints[6] = 0.0  # Close gripper (7th joint)

        action = ArticulationAction(joint_positions=current_joints)
        self.robot.apply_action(action)

        self.motion_complete = True
        self.current_action = None
        print(f"Robot {self.robot_name} closed gripper")

    def halt_motion(self):
        """Immediately halt robot motion"""
        # Apply current joint positions to stop motion
        current_joints = self.robot.get_joint_positions()
        action = ArticulationAction(joint_positions=current_joints)
        self.robot.apply_action(action)

        self.is_moving = False
        self.current_action = None
        print(f"Robot {self.robot_name} motion halted")

    def on_collision(self, actor0, actor1):
        """Called when collision is detected involving this robot"""
        self.collision_detected = True
        self.collision_actors = f"{actor0} <-> {actor1}"
        print(f"Robot {self.robot_name} collision detected: {self.collision_actors}")
        self.halt_motion()

    def on_motion_complete(self):
        """Called when motion is completed (currently handled internally)"""
        self.motion_complete = True
        self.is_moving = False
        print(f"Robot {self.robot_name} motion completed")
