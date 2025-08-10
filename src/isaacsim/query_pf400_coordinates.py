#!/usr/bin/env python3
"""
Query script to get real PF400 joint coordinates for workcell locations.
Uses goto_pose on world positions and relies on run.py to print joint angles.
"""

import json
import zmq
import time
import sys
from typing import Dict, List


class PF400CoordinateQuerier:
    """Query PF400 robot by moving to world positions and capturing joint angles"""

    def __init__(self, zmq_server_url: str = "tcp://localhost:5557"):
        self.zmq_server_url = zmq_server_url
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.connected = False

    def connect(self) -> bool:
        """Connect to PF400 ZMQ server"""
        try:
            self.socket.connect(self.zmq_server_url)
            # Test connection
            test_response = self.send_command({"action": "get_status"})
            if test_response.get("status") == "success":
                self.connected = True
                print(f"✓ Connected to PF400 at {self.zmq_server_url}")
                return True
            else:
                print(f"✗ Failed to connect: {test_response}")
                return False
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False

    def send_command(self, command: dict, timeout_ms: int = 10000) -> dict:
        """Send command to PF400 and return response"""
        try:
            # Set timeout
            self.socket.setsockopt(zmq.RCVTIMEO, timeout_ms)

            # Send command
            self.socket.send_string(json.dumps(command))

            # Receive response
            response_str = self.socket.recv_string()
            return json.loads(response_str)

        except zmq.Again:
            return {"status": "error", "message": "Timeout waiting for response"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def move_to_position_and_wait(self, position: List[float], orientation: List[float], location_name: str) -> Dict:
        """Move to world position and wait for completion - run.py will print joint angles"""
        print(f"\nMoving PF400 to {location_name} at world position {position}...")

        # Send goto_pose command with world coordinates
        goto_command = {
            "action": "goto_pose",
            "position": position,
            "orientation": orientation
        }

        response = self.send_command(goto_command)
        if response.get("status") != "success":
            return {"error": f"Failed to move to {location_name}: {response.get('message')}"}

        # Wait for motion to complete
        print("  Waiting for motion to complete...")
        print("  Watch run.py output for joint angles when motion completes!")

        max_wait = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = self.send_command({"action": "get_status"})
            if status.get("status") == "success":
                if status.get("collision_detected", False):
                    return {"error": f"Collision detected while moving to {location_name}"}

                if status.get("motion_complete", False) or not status.get("is_moving", False):
                    print("  Motion completed! Check run.py output for joint angles.")
                    # Get final joint positions for reference
                    joints_response = self.send_command({"action": "get_joints"})
                    if joints_response.get("status") == "success":
                        joints = joints_response.get("joint_angles", [])
                        print(f"  Final joint angles: {joints}")
                        return {"joints": joints, "position": position}
                    break

            time.sleep(0.5)
        else:
            return {"error": f"Motion to {location_name} did not complete within {max_wait} seconds"}

        return {"error": "Could not retrieve final joint angles"}

    def query_all_locations(self) -> Dict[str, List[float]]:
        """Move PF400 to all workcell locations and capture joint angles"""
        if not self.connected:
            print("Not connected to PF400")
            return {}

        # Define world positions based on the Xforms created in run.py
        world_locations = {
            "high_position": {
                "position": [0.245, 0.0, 1.0],  # high world position
                "orientation": [1.0, 0.0, 0.0, 0.0]
            },
            "approach_position": {
                "position": [0.245, 0.0, 0.6],  # approach world position
                "orientation": [1.0, 0.0, 0.0, 0.0]
            },
            "platform1": {
                "position": [0.3, 0.3, 0.3],  # platform1_dropoff world position
                "orientation": [1.0, 0.0, 0.0, 0.0]  # neutral orientation
            },
            "platform2": {
                "position": [0.3, -0.3, 0.3],  # platform2_dropoff world position
                "orientation": [1.0, 0.0, 0.0, 0.0]
            },
        }

        results = {}

        print("Moving PF400 to all workcell world positions...")
        print("Watch Isaac Sim console - run.py will print joint angles at each location!")
        print()

        for location_name, pose_data in world_locations.items():
            result = self.move_to_position_and_wait(
                pose_data["position"],
                pose_data["orientation"],
                location_name
            )

            if "error" in result:
                print(f"Error for {location_name}: {result['error']}")
                results[location_name] = "ERROR"
            else:
                results[location_name] = result["joints"]
                print(f"{location_name}: {result['joints']}")

            # Small pause between movements
            time.sleep(5)

        return results

    def cleanup(self):
        """Clean up ZMQ resources"""
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()


def print_workcell_yaml_format(coordinates: Dict[str, List[float]]):
    """Print coordinates in workcell.yaml format"""
    if not coordinates:
        print("\nNo coordinates to format")
        return

    print("\n" + "="*60)
    print("WORKCELL.YAML FORMAT - Copy these coordinates:")
    print("="*60)

    for location_name, joints in coordinates.items():
        if joints != "ERROR" and len(joints) >= 6:
            # Format as YAML list with proper indentation
            joints_str = "\n    ".join([f"- {joint}" for joint in joints])
            print(f"\n# {location_name.upper()}")
            print(f"  lookup:")
            print(f"    pf400:")
            print(f"    {joints_str}")
        else:
            print(f"\n# {location_name.upper()} - ERROR OR INCOMPLETE")


def main():
    """Main function to query coordinates"""
    print("PF400 Coordinate Querier (Physical Movement)")
    print("===========================================")
    print("This will physically move the PF400 to each location!")
    print("Watch Isaac Sim and run.py console output for joint angles.")
    print()

    querier = PF400CoordinateQuerier()

    try:
        if not querier.connect():
            print("Failed to connect to PF400. Is Isaac Sim running with run.py?")
            sys.exit(1)

        # Move to all locations and capture coordinates
        coordinates = querier.query_all_locations()

        # Print results in workcell format
        print_workcell_yaml_format(coordinates)

        print(f"\nMovement sequence complete!")
        print("Check Isaac Sim console output for detailed joint angle logs from run.py")

    except KeyboardInterrupt:
        print("\nQuery interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        querier.cleanup()


if __name__ == "__main__":
    main()