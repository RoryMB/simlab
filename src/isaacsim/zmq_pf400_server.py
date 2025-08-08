import numpy as np
from isaacsim.core.utils.types import ArticulationAction
from zmq_robot_server import ZMQ_Robot_Server

class ZMQ_PF400_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot with integrated control"""
    
    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        super().__init__(simulation_app, robot, robot_name, port, motion_type)
        
        # PF400 joint limits based on PF400 specifications
        # Joint 1 (Z/vertical): Typically 0 to 350mm
        # Joint 2 (Shoulder): -180 to 180 degrees  
        # Joint 3 (Elbow): 10 to 350 degrees (converted to -180 to 180 range in kinematics)
        # Joint 4 (Gripper rotation): -180 to 180 degrees
        # Joint 5 (Gripper tilt): -90 to 90 degrees
        # Joint 6 (Rail): 0 to 600mm (X-axis movement)
        # Joint 7 (Gripper): 0 (closed) to 1 (open)
        self.joint_limits = [
            (0.0, 0.35),      # Joint 1: Z (meters)
            (-3.14159, 3.14159),  # Joint 2: Shoulder (radians)
            (0.17453, 6.10865),   # Joint 3: Elbow (10-350 degrees in radians)
            (-3.14159, 3.14159),  # Joint 4: Gripper rotation (radians)
            (-1.5708, 1.5708),    # Joint 5: Gripper tilt (radians)
            (0.0, 0.6),       # Joint 6: Rail (meters)
            (0.0, 1.0),       # Joint 7: Gripper (0=closed, 1=open)
        ]
        
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

            # Validate joint limits
            for i, (angle, (min_val, max_val)) in enumerate(zip(joint_angles, self.joint_limits)):
                if not (min_val <= angle <= max_val):
                    return self.create_error_response(f"Joint {i+1} angle {angle} out of bounds [{min_val}, {max_val}]")

            # Store command for execution in update loop
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

        elif action == "move_cartesian":
            cartesian_coords = request.get("cartesian_coordinates", [])
            
            if len(cartesian_coords) != 4 and len(cartesian_coords) != 6:
                return self.create_error_response(f"Expected 4 or 6 cartesian coordinates, got {len(cartesian_coords)}")
                
            try:
                # Convert to joint angles using simplified IK
                joint_angles = self.simple_cartesian_to_joints(cartesian_coords)
                
                # Store command for execution in update loop
                self.current_action = "move_joints"
                self.target_joints = np.array(joint_angles)
                self.is_moving = True
                self.motion_complete = False
                
                return self.create_success_response("cartesian move queued", 
                                                 cartesian_coordinates=cartesian_coords,
                                                 joint_angles=joint_angles)
            except Exception as e:
                return self.create_error_response(f"Failed to convert cartesian position: {str(e)}")

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
                return self.create_success_response("status retrieved",
                                                 joint_angles=joint_positions.tolist(),
                                                 gripper_state="open" if self.gripper_open else "closed",
                                                 is_homed=np.allclose(joint_positions, self.home_position, atol=0.01),
                                                 is_moving=self.is_moving,
                                                 collision_detected=self.collision_detected,
                                                 motion_complete=self.motion_complete)
            except Exception as e:
                return self.create_error_response(f"Failed to get status: {str(e)}")

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def simple_cartesian_to_joints(self, cartesian_coords):
        """
        Simple cartesian to joint conversion for PF400
        This is a simplified version - real implementation would use PF400 kinematics
        """
        # Expected format: [x, y, z, yaw] or [x, y, z, yaw, pitch, roll]
        x, y, z = cartesian_coords[0], cartesian_coords[1], cartesian_coords[2]
        yaw = cartesian_coords[3] if len(cartesian_coords) > 3 else 0.0
        
        # Simplified inverse kinematics for demonstration
        # In reality, this would use the full PF400 kinematics calculations
        
        # Joint 1: Z position (vertical)
        joint1 = max(0.0, min(0.35, z))
        
        # Joint 2: Shoulder angle (simplified)
        joint2 = np.arctan2(y, x)
        
        # Joint 3: Elbow angle (simplified - keep at reasonable position)
        joint3 = 1.5708  # 90 degrees
        
        # Joint 4: Gripper rotation (use yaw)
        joint4 = yaw
        
        # Joint 5: Gripper tilt (keep level)
        joint5 = 0.0
        
        # Joint 6: Rail position (use x coordinate)
        joint6 = max(0.0, min(0.6, x))
        
        # Joint 7: Gripper (default closed)
        joint7 = 0.0
        
        return [joint1, joint2, joint3, joint4, joint5, joint6, joint7]

    def validate_joint_limits(self, joint_angles):
        """Validate that joint angles are within PF400 limits"""
        for i, (angle, (min_val, max_val)) in enumerate(zip(joint_angles, self.joint_limits)):
            if not (min_val <= angle <= max_val):
                return False, f"Joint {i+1} angle {angle} out of bounds [{min_val}, {max_val}]"
        return True, "Valid"

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