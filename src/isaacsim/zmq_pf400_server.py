import numpy as np
from zmq_robot_server import ZMQ_Robot_Server

class ZMQ_PF400_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot"""
    
    def __init__(self, simulation_app, robot, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_name, port)
        
        # PF400 joint limits based on PF400 specifications
        # Joint 1 (Z/vertical): Typically 0 to 350mm
        # Joint 2 (Shoulder): -180 to 180 degrees  
        # Joint 3 (Elbow): 10 to 350 degrees (converted to -180 to 180 range in kinematics)
        # Joint 4 (Gripper rotation): -180 to 180 degrees
        # Joint 5 (Gripper tilt): -90 to 90 degrees
        # Joint 6 (Rail): 0 to 600mm (X-axis movement)
        self.joint_limits = [
            (0.0, 0.35),      # Joint 1: Z (meters)
            (-3.14159, 3.14159),  # Joint 2: Shoulder (radians)
            (0.17453, 6.10865),   # Joint 3: Elbow (10-350 degrees in radians)
            (-3.14159, 3.14159),  # Joint 4: Gripper rotation (radians)
            (-1.5708, 1.5708),    # Joint 5: Gripper tilt (radians)
            (0.0, 0.6),       # Joint 6: Rail (meters)
        ]
        
        # PF400 home position (safe position)
        self.home_position = [0.2, 0.0, 1.5708, 0.0, 0.0, 0.3]  # 200mm Z, 90deg elbow, 300mm rail
        
        # Gripper state
        self.gripper_open = False
        
    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci"""
        action = request.get("action", "")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])

            if len(joint_angles) != 6:
                return self.create_error_response(f"Expected 6 joint angles, got {len(joint_angles)}")

            # Validate joint limits
            for i, (angle, (min_val, max_val)) in enumerate(zip(joint_angles, self.joint_limits)):
                if not (min_val <= angle <= max_val):
                    return self.create_error_response(f"Joint {i+1} angle {angle} out of bounds [{min_val}, {max_val}]")

            try:
                self.robot.set_joint_positions(np.array(joint_angles))
                return self.create_success_response("moved", joint_angles=joint_angles)
            except Exception as e:
                return self.create_error_response(f"Failed to move robot: {str(e)}")

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
                # For now, we'll use a simplified inverse kinematics
                # In a full implementation, we'd use the PF400 kinematics class
                joint_angles = self.simple_cartesian_to_joints(cartesian_coords)
                
                self.robot.set_joint_positions(np.array(joint_angles))
                return self.create_success_response("moved to cartesian position", 
                                                 cartesian_coordinates=cartesian_coords,
                                                 joint_angles=joint_angles)
            except Exception as e:
                return self.create_error_response(f"Failed to move to cartesian position: {str(e)}")

        elif action == "home":
            try:
                self.robot.set_joint_positions(np.array(self.home_position))
                return self.create_success_response("homed", joint_angles=self.home_position)
            except Exception as e:
                return self.create_error_response(f"Failed to home robot: {str(e)}")

        elif action == "gripper_open":
            try:
                self.gripper_open = True
                return self.create_success_response("gripper opened", gripper_state="open")
            except Exception as e:
                return self.create_error_response(f"Failed to open gripper: {str(e)}")

        elif action == "gripper_close":
            try:
                self.gripper_open = False
                return self.create_success_response("gripper closed", gripper_state="closed")
            except Exception as e:
                return self.create_error_response(f"Failed to close gripper: {str(e)}")

        elif action == "get_status":
            try:
                joint_positions = self.robot.get_joint_positions()
                return self.create_success_response("status retrieved",
                                                 joint_angles=joint_positions.tolist(),
                                                 gripper_state="open" if self.gripper_open else "closed",
                                                 is_homed=np.allclose(joint_positions, self.home_position, atol=0.01))
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
        
        return [joint1, joint2, joint3, joint4, joint5, joint6]

    def validate_joint_limits(self, joint_angles):
        """Validate that joint angles are within PF400 limits"""
        for i, (angle, (min_val, max_val)) in enumerate(zip(joint_angles, self.joint_limits)):
            if not (min_val <= angle <= max_val):
                return False, f"Joint {i+1} angle {angle} out of bounds [{min_val}, {max_val}]"
        return True, "Valid"