"""
zmq_ppc.py - ZMQ Pick Place and Collision Detection Client (Orchestrator)
Orchestrates PF400 robot pick and place operations by sending commands
to the robot's ZMQ server (like MADSci does)
"""

import time
import zmq
import json
import argparse

class PF400Orchestrator:
    """ZMQ client for orchestrating PF400 robot operations"""

    def __init__(self, port=5557, timeout=10000):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{port}")
        self.socket.setsockopt(zmq.RCVTIMEO, timeout)  # 10 second timeout
        print(f"Connected to PF400 robot server on port {port}")

    def send_command(self, command):
        """Send command to robot server and return response"""
        print(f"Sending command: {command}")

        try:
            self.socket.send_json(command)
            response = self.socket.recv_json()
            print(f"Received response: {response}")
            return response
        except zmq.Again:
            print("Error: Command timed out")
            return {"status": "error", "message": "Command timed out"}
        except Exception as e:
            print(f"Error sending command: {e}")
            return {"status": "error", "message": str(e)}

    def wait_for_motion_complete(self, check_interval=0.5, max_wait=30):
        """Wait for robot to complete current motion"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = self.send_command({"action": "get_status"})

            if response.get("status") == "success":
                if response.get("collision_detected", False):
                    print("Error: Collision detected during motion")
                    return False
                elif response.get("motion_complete", False) or not response.get("is_moving", False):
                    print("Robot completed motion")
                    return True

            time.sleep(check_interval)

        print(f"Warning: Robot did not complete motion within {max_wait} seconds")
        return False

    def home_robot(self):
        """Move robot to home position"""
        print("=== HOMING ROBOT ===")
        response = self.send_command({"action": "home"})
        if response.get("status") == "success":
            return self.wait_for_motion_complete()
        return False

    def move_to_pickup_position(self):
        """Move robot to pickup position above microplate (0.3, 0.3, 0.3)"""
        print("=== MOVING TO PICKUP POSITION ===")

        # Joint configuration to reach pickup position
        # Based on microplate at (0.3, 0.3, 0.3)
        pickup_joints = [
            0.25,   # Z height to be above plate
            0.785,  # Shoulder angle (atan2(0.3, 0.3) ≈ 0.785)
            1.57,   # Elbow at 90 degrees
            0.0,    # No gripper rotation
            -0.3,   # Tilt down to reach plate
            0.3,    # Rail position for X coordinate
            1.0     # Gripper open for pickup
        ]

        response = self.send_command({
            "action": "move_joints",
            "joint_angles": pickup_joints
        })

        if response.get("status") == "success":
            return self.wait_for_motion_complete()
        return False

    def move_to_dropoff_position(self):
        """Move robot to dropoff position above platform"""
        print("=== MOVING TO DROPOFF POSITION ===")

        # Joint configuration to reach dropoff position
        # Platform is at (0.73, 0.75, -0.205), so we move above it
        dropoff_joints = [
            0.15,   # Z height above platform
            0.785,  # Shoulder angle to reach Y position
            2.0,    # Elbow angle for reach
            1.57,   # Gripper rotation
            0.0,    # No tilt
            0.6,    # Rail position (clipped to joint limit)
            0.0     # Gripper closed
        ]

        response = self.send_command({
            "action": "move_joints",
            "joint_angles": dropoff_joints
        })

        if response.get("status") == "success":
            return self.wait_for_motion_complete()
        return False

    def move_to_safe_height(self):
        """Move robot up to safe height while maintaining position"""
        print("=== MOVING TO SAFE HEIGHT ===")

        # Get current status to maintain X,Y position but increase Z
        status = self.send_command({"action": "get_status"})
        if status.get("status") != "success":
            return False

        current_joints = status["joint_angles"]
        current_joints[0] += 0.05  # Lift Z by 5cm
        current_joints[0] = min(current_joints[0], 0.35)  # Respect joint limits

        response = self.send_command({
            "action": "move_joints",
            "joint_angles": current_joints
        })

        if response.get("status") == "success":
            return self.wait_for_motion_complete()
        return False

    def close_gripper(self):
        """Close gripper to grasp object"""
        print("=== CLOSING GRIPPER ===")
        response = self.send_command({"action": "gripper_close"})
        time.sleep(1)  # Give time for gripper action
        return response.get("status") == "success"

    def open_gripper(self):
        """Open gripper to release object"""
        print("=== OPENING GRIPPER ===")
        response = self.send_command({"action": "gripper_open"})
        time.sleep(1)  # Give time for gripper action
        return response.get("status") == "success"

    def get_status(self):
        """Get current robot status"""
        response = self.send_command({"action": "get_status"})
        return response

    def pick_and_place_sequence(self):
        """Execute complete pick and place sequence"""
        print("=== STARTING PICK AND PLACE SEQUENCE ===")

        # Step 1: Home robot
        if not self.home_robot():
            print("Error: Failed to home robot")
            return False

        # Step 2: Move to pickup position
        if not self.move_to_pickup_position():
            print("Error: Failed to reach pickup position")
            return False

        # Step 3: Close gripper to pick up plate
        if not self.close_gripper():
            print("Error: Failed to close gripper")
            return False

        # Step 4: Move to safe height
        if not self.move_to_safe_height():
            print("Error: Failed to lift to safe height")
            # Continue anyway

        # Step 5: Move to dropoff position
        if not self.move_to_dropoff_position():
            print("Error: Failed to reach dropoff position")
            return False

        # Step 6: Open gripper to drop plate
        if not self.open_gripper():
            print("Error: Failed to open gripper")
            return False

        # Step 7: Return to home
        if not self.home_robot():
            print("Error: Failed to return home")
            return False

        print("=== PICK AND PLACE SEQUENCE COMPLETED SUCCESSFULLY ===")
        return True

    def collision_test_sequence(self):
        """Test collision detection by commanding risky movements"""
        print("=== TESTING COLLISION DETECTION ===")

        # First home the robot
        self.home_robot()

        # Move robot to potentially collide with ground
        print("Commanding robot to move to potential collision position...")
        collision_joints = [
            0.0,    # Move Z to minimum (may hit ground)
            0.0,    # Neutral shoulder
            1.57,   # 90 degree elbow
            0.0,    # No rotation
            0.0,    # No tilt
            0.3,    # Mid rail position
            1.0     # Open gripper
        ]

        response = self.send_command({
            "action": "move_joints",
            "joint_angles": collision_joints
        })

        if response.get("status") != "success":
            print("Error: Failed to send collision test command")
            return False

        # Wait and check for collision
        time.sleep(3)
        status = self.get_status()

        if status.get("collision_detected", False):
            print("SUCCESS: Collision detected as expected!")
            return True
        else:
            print("Warning: No collision detected - may need to adjust test")
            return False

    def manual_joint_move(self, joints):
        """Move to specific joint positions"""
        if len(joints) != 7:
            print("Error: Need exactly 7 joint values")
            return False

        response = self.send_command({
            "action": "move_joints",
            "joint_angles": joints
        })

        if response.get("status") == "success":
            return self.wait_for_motion_complete()
        return False

    def interactive_mode(self):
        """Interactive mode for manual robot control"""
        print("=== ENTERING INTERACTIVE MODE ===")
        print("Available commands:")
        print("  home - Move to home position")
        print("  pickup - Move to pickup position")
        print("  dropoff - Move to dropoff position")
        print("  safe - Move to safe height")
        print("  close - Close gripper")
        print("  open - Open gripper")
        print("  status - Get robot status")
        print("  sequence - Run full pick and place sequence")
        print("  collision - Test collision detection")
        print("  joints <j1> <j2> ... <j7> - Move to specific joint angles")
        print("  quit - Exit interactive mode")

        while True:
            try:
                cmd = input("\nEnter command: ").strip().lower().split()

                if not cmd:
                    continue

                if cmd[0] == "quit":
                    break
                elif cmd[0] == "home":
                    self.home_robot()
                elif cmd[0] == "pickup":
                    self.move_to_pickup_position()
                elif cmd[0] == "dropoff":
                    self.move_to_dropoff_position()
                elif cmd[0] == "safe":
                    self.move_to_safe_height()
                elif cmd[0] == "close":
                    self.close_gripper()
                elif cmd[0] == "open":
                    self.open_gripper()
                elif cmd[0] == "status":
                    status = self.get_status()
                    print(json.dumps(status, indent=2))
                elif cmd[0] == "sequence":
                    self.pick_and_place_sequence()
                elif cmd[0] == "collision":
                    self.collision_test_sequence()
                elif cmd[0] == "joints" and len(cmd) == 8:
                    try:
                        joints = [float(x) for x in cmd[1:]]
                        self.manual_joint_move(joints)
                    except ValueError:
                        print("Error: Invalid joint values - must be numbers")
                else:
                    print(f"Error: Unknown command or wrong number of arguments: {' '.join(cmd)}")

            except KeyboardInterrupt:
                break

        print("Exiting interactive mode")

    def close(self):
        """Close ZMQ connection"""
        self.socket.close()
        self.context.term()

def main():
    parser = argparse.ArgumentParser(description="PF400 Robot Orchestrator")
    parser.add_argument("--port", type=int, default=5557, help="Robot server ZMQ port")
    parser.add_argument("--mode", choices=["sequence", "collision", "interactive"],
                       default="interactive", help="Operation mode")
    args = parser.parse_args()

    # Create orchestrator
    orchestrator = PF400Orchestrator(port=args.port)

    try:
        if args.mode == "sequence":
            success = orchestrator.pick_and_place_sequence()
            if success:
                print("Pick and place sequence completed successfully")
            else:
                print("Error: Pick and place sequence failed")

        elif args.mode == "collision":
            success = orchestrator.collision_test_sequence()
            if success:
                print("Collision test completed successfully")
            else:
                print("Error: Collision test failed")

        elif args.mode == "interactive":
            orchestrator.interactive_mode()

    finally:
        orchestrator.close()

if __name__ == "__main__":
    main()