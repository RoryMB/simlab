#!/usr/bin/env python3
"""
Isaac Sim Direct Command Script Template

Usage:
    1. Copy this file to a new location (e.g., cp command_template.py my_test.py)
    2. Edit ROBOT_PORTS and COMMANDS below
    3. Start Isaac Sim with your scene
    4. Run: python my_test.py
    5. Delete when done

This script talks directly to Isaac Sim via ZMQ, bypassing MADSci entirely.
"""

import json
import sys
import time

import zmq


# ============================================================================
# CONFIGURATION - Edit this section
# ============================================================================

# Robot name -> ZMQ port mapping
# These must match the ports in your Isaac Sim script (e.g., run_phys.py)
ROBOT_PORTS = {
    "pf400_0": 5557,
    "thermocycler_0": 5560,
    # "sealer_0": 5558,
    # "peeler_0": 5559,
    # "hidex_0": 5561,
    # "ot2_0": 5556,
}

# Stop script on first error/collision? Set False to log and continue.
STOP_ON_ERROR = True

# Commands to execute sequentially
# Each command needs "robot" (name from ROBOT_PORTS) and "action"
# Additional fields depend on the action type
COMMANDS = [
    # Example: Move PF400 to a prim location in the scene
    # {"robot": "pf400_0", "action": "goto_prim", "prim_name": "/World/target"},

    # Example: Move PF400 to specific joint positions (7 joints)
    # {"robot": "pf400_0", "action": "move_joints", "joint_positions": [0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0]},

    # Example: Gripper control
    # {"robot": "pf400_0", "action": "gripper_close"},
    # {"robot": "pf400_0", "action": "gripper_open"},

    # Example: Move to world pose (position [x,y,z] and orientation [w,x,y,z])
    # {"robot": "pf400_0", "action": "goto_pose", "position": [0.5, 0.3, 0.4], "orientation": [1.0, 0.0, 0.0, 0.0]},

    # Example: Get current joint positions (prints result, doesn't wait)
    # {"robot": "pf400_0", "action": "get_joints"},

    # Example: Thermocycler operations
    # {"robot": "thermocycler_0", "action": "open"},
    # {"robot": "thermocycler_0", "action": "close"},
    # {"robot": "thermocycler_0", "action": "run_program", "program_number": 5},

    # Example: Sealer/Peeler operations
    # {"robot": "sealer_0", "action": "seal"},
    # {"robot": "peeler_0", "action": "peel"},

    # Example: Hidex operations
    # {"robot": "hidex_0", "action": "open"},
    # {"robot": "hidex_0", "action": "close"},
    # {"robot": "hidex_0", "action": "run_assay", "assay_name": "TestAssay"},
]


# ============================================================================
# RUNNER CODE - No need to edit below this line
# ============================================================================

# Actions that queue motion and require waiting for completion
MOTION_ACTIONS = {
    "move_joints",
    "goto_pose",
    "goto_prim",
    "gripper_open",
    "gripper_close",
    "open",
    "close",
    "open_lid",
    "close_lid",
    "seal",
    "peel",
}


class CommandRunner:
    """Executes commands against Isaac Sim ZMQ servers."""

    def __init__(self, robot_ports: dict, stop_on_error: bool = True):
        self.robot_ports = robot_ports
        self.stop_on_error = stop_on_error
        self.context = zmq.Context()
        self.sockets = {}

    def connect(self):
        """Connect to all robot ZMQ servers."""
        for robot_name, port in self.robot_ports.items():
            socket = self.context.socket(zmq.REQ)
            socket.connect(f"tcp://localhost:{port}")
            self.sockets[robot_name] = socket
            print(f"Connected to {robot_name} on port {port}")

    def cleanup(self):
        """Close all connections."""
        for socket in self.sockets.values():
            socket.close()
        self.context.term()

    def send_command(self, robot_name: str, command: dict, timeout_ms: int = 5000) -> dict:
        """Send command and return response."""
        if robot_name not in self.sockets:
            return {"status": "error", "message": f"Unknown robot: {robot_name}"}

        socket = self.sockets[robot_name]
        try:
            socket.send_string(json.dumps(command))
            if socket.poll(timeout_ms):
                response = json.loads(socket.recv_string())
                return response
            else:
                return {"status": "error", "message": "Timeout waiting for response"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_status(self, robot_name: str) -> dict:
        """Get robot status."""
        return self.send_command(robot_name, {"action": "get_status"})

    def wait_for_completion(self, robot_name: str, max_wait: float = 60.0) -> tuple[bool, str]:
        """Wait for robot motion to complete. Returns (success, message)."""
        start = time.time()
        while time.time() - start < max_wait:
            response = self.get_status(robot_name)

            if response.get("status") != "success":
                return False, f"Failed to get status: {response.get('message', 'Unknown error')}"

            data = response.get("data", {})

            if data.get("collision_detected", False):
                return False, "Collision detected"

            if data.get("motion_complete", True) and not data.get("is_moving", False):
                return True, "Motion complete"

            time.sleep(0.05)

        return False, f"Timeout after {max_wait}s"

    def execute(self, commands: list) -> bool:
        """Execute command sequence. Returns True if all succeeded."""
        self.connect()
        all_success = True

        try:
            for i, cmd in enumerate(commands):
                robot_name = cmd.get("robot")
                action = cmd.get("action")

                if not robot_name or not action:
                    print(f"[{i+1}/{len(commands)}] ERROR: Command missing 'robot' or 'action': {cmd}")
                    if self.stop_on_error:
                        return False
                    all_success = False
                    continue

                # Build the ZMQ command (everything except 'robot' key)
                zmq_cmd = {k: v for k, v in cmd.items() if k != "robot"}

                print(f"[{i+1}/{len(commands)}] {robot_name}: {action}", end="", flush=True)

                # Send command
                response = self.send_command(robot_name, zmq_cmd)

                if response.get("status") != "success":
                    print(f" -> FAILED: {response.get('message', 'Unknown error')}")
                    if self.stop_on_error:
                        return False
                    all_success = False
                    continue

                # For motion actions, wait for completion
                if action in MOTION_ACTIONS:
                    print(" -> queued, waiting...", end="", flush=True)
                    success, msg = self.wait_for_completion(robot_name)
                    if success:
                        print(f" -> {msg}")
                    else:
                        print(f" -> FAILED: {msg}")
                        if self.stop_on_error:
                            return False
                        all_success = False
                else:
                    # Non-motion actions (like get_joints) complete immediately
                    print(f" -> OK")
                    if "data" in response:
                        print(f"    Data: {response['data']}")

        finally:
            self.cleanup()

        return all_success


def main():
    if not COMMANDS:
        print("No commands defined. Edit the COMMANDS list in this script.")
        sys.exit(1)

    if not ROBOT_PORTS:
        print("No robots defined. Edit the ROBOT_PORTS dict in this script.")
        sys.exit(1)

    # Check all referenced robots have ports defined
    for cmd in COMMANDS:
        robot = cmd.get("robot")
        if robot and robot not in ROBOT_PORTS:
            print(f"ERROR: Robot '{robot}' used in COMMANDS but not defined in ROBOT_PORTS")
            sys.exit(1)

    print(f"Executing {len(COMMANDS)} commands (stop_on_error={STOP_ON_ERROR})")
    print("-" * 60)

    runner = CommandRunner(ROBOT_PORTS, stop_on_error=STOP_ON_ERROR)
    success = runner.execute(COMMANDS)

    print("-" * 60)
    if success:
        print("All commands completed successfully")
    else:
        print("Some commands failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
