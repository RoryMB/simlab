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

        # Get positions for all reference points
        print("Getting reference positions...")

        # Get high position
        high_response = self.send_command({
            "action": "get_relative_pose",
            "prim_path": "/World/high"
        })
        if high_response.get("status") != "success":
            print("Error: Failed to get /World/high position")
            return False
        high_pos = high_response["position"]
        high_orient = high_response["orientation"]

        # Get side position
        side_response = self.send_command({
            "action": "get_relative_pose",
            "prim_path": "/World/side"
        })
        if side_response.get("status") != "success":
            print("Error: Failed to get /World/side position")
            return False
        side_pos = side_response["position"]
        side_orient = side_response["orientation"]

        # Get coll position
        coll_response = self.send_command({
            "action": "get_relative_pose",
            "prim_path": "/World/coll"
        })
        if coll_response.get("status") != "success":
            print("Error: Failed to get /World/coll position")
            return False
        coll_pos = coll_response["position"]
        coll_orient = coll_response["orientation"]

        print("All positions retrieved successfully")

        # Step 1: Move to high position
        print("Moving to high position...")
        response = self.send_command({
            "action": "goto_pose",
            "position": high_pos,
            "orientation": high_orient
        })
        if response.get("status") != "success" or not self.wait_for_motion_complete():
            print("Error: Failed to reach high position")
            return False

        # Step 2: Move to side position
        print("Moving to side position...")
        response = self.send_command({
            "action": "goto_pose",
            "position": side_pos,
            "orientation": side_orient
        })
        if response.get("status") != "success" or not self.wait_for_motion_complete():
            print("Error: Failed to reach side position")
            return False

        # Step 3: Close gripper to grab
        if not self.close_gripper():
            print("Error: Failed to close gripper")
            return False

        # Step 4: Move back to high position
        print("Moving back to high position...")
        response = self.send_command({
            "action": "goto_pose",
            "position": high_pos,
            "orientation": high_orient
        })
        if response.get("status") != "success" or not self.wait_for_motion_complete():
            print("Error: Failed to return to high position")
            return False

        # Step 5: Move to coll position
        print("Moving to coll position...")
        response = self.send_command({
            "action": "goto_pose",
            "position": coll_pos,
            "orientation": coll_orient
        })
        if response.get("status") != "success" or not self.wait_for_motion_complete():
            print("Error: Failed to reach coll position")
            return False

        # Step 6: Open gripper to drop
        if not self.open_gripper():
            print("Error: Failed to open gripper")
            return False

        print("=== PICK AND PLACE SEQUENCE COMPLETED SUCCESSFULLY ===")
        return True

    def move_joints(self, joints):
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
        print("  get_relative_pose <prim_path> - Get pose of prim relative to robot")
        print("  goto_pose <x> <y> <z> <w> <x> <y> <z> - Move to relative position and orientation")
        print("  close - Close gripper")
        print("  open - Open gripper")
        print("  status - Get robot status")
        print("  sequence - Run full pick and place sequence")
        print("  move_joints <j1> <j2> ... <j7> - Move to specific joint angles")
        print("  quit - Exit interactive mode")

        while True:
            try:
                cmd = input("\nEnter command: ").strip().split()

                if not cmd:
                    continue

                if cmd[0] == "quit":
                    break
                elif cmd[0] == "get_relative_pose" and len(cmd) == 2:
                    response = self.send_command({
                        "action": "get_relative_pose",
                        "prim_path": cmd[1]
                    })
                    print(json.dumps(response, indent=2))
                elif cmd[0] == "goto_pose" and len(cmd) == 8:
                    try:
                        position = [float(cmd[1]), float(cmd[2]), float(cmd[3])]
                        orientation = [float(cmd[4]), float(cmd[5]), float(cmd[6]), float(cmd[7])]
                        response = self.send_command({
                            "action": "goto_pose",
                            "position": position,
                            "orientation": orientation
                        })
                        if response.get("status") == "success":
                            self.wait_for_motion_complete()
                        else:
                            print(json.dumps(response, indent=2))
                    except ValueError:
                        print("Error: Invalid pose values - must be numbers")
                elif cmd[0] == "close":
                    self.close_gripper()
                elif cmd[0] == "open":
                    self.open_gripper()
                elif cmd[0] == "status":
                    status = self.get_status()
                    print(json.dumps(status, indent=2))
                elif cmd[0] == "sequence":
                    self.pick_and_place_sequence()
                elif cmd[0] == "move_joints" and len(cmd) == 8:
                    try:
                        joints = [float(x) for x in cmd[1:]]
                        self.move_joints(joints)
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
    parser.add_argument("--mode", choices=["sequence", "interactive"], default="interactive", help="Operation mode")
    args = parser.parse_args()

    # Create orchestrator
    orchestrator = PF400Orchestrator(port=args.port)

    if args.mode == "sequence":
        time.sleep(10)
        success = orchestrator.pick_and_place_sequence()
        if success:
            print("Pick and place sequence completed successfully")
        else:
            print("Error: Pick and place sequence failed")

    elif args.mode == "interactive":
        orchestrator.interactive_mode()

if __name__ == "__main__":
    main()
