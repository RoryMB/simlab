#!/usr/bin/env python3
"""
Isaac Sim Direct Command Script for Scaling MVP

This script talks directly to Isaac Sim via ZMQ ROUTER, bypassing MADSci entirely.
Uses DEALER sockets with identity-based routing.

Usage:
    1. Start Isaac Sim: python run.py
    2. Edit ENV_ID and COMMANDS below
    3. Run: python command.py
"""

import json
import sys
import time

import zmq


# ============================================================================
# CONFIGURATION - Edit this section
# ============================================================================

# Which environment to control (0-4)
ENV_ID = 0

# ZMQ ROUTER server (single multiplexed port)
ZMQ_SERVER_URL = "tcp://localhost:5555"

# Stop script on first error/collision? Set False to log and continue.
STOP_ON_ERROR = True

# Commands to execute sequentially
# Each command needs "robot" (pf400, thermocycler, or peeler) and "action"
COMMANDS = [
    # === Calibration: Get current joint positions ===
    # {"robot": "pf400", "action": "get_joints"},

    # === PF400 Commands ===
    # Move to a prim location (xform) in the scene
    # {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/home"},
    # {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/staging_hover"},
    # {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/staging"},

    # Move to specific joint angles (7 joints)
    # {"robot": "pf400", "action": "move_joints", "joint_angles": [0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0]},

    # Gripper control
    # {"robot": "pf400", "action": "gripper_open"},
    # {"robot": "pf400", "action": "gripper_close"},

    # Get status
    # {"robot": "pf400", "action": "get_status"},

    # === Thermocycler Commands ===
    # {"robot": "thermocycler", "action": "open"},
    # {"robot": "thermocycler", "action": "close"},

    # === Peeler Commands ===
    # {"robot": "peeler", "action": "peel"},

    # === Safe calibration sequence ===
    # Key principles:
    # 1. Open lids BEFORE approaching devices
    # 2. Always return to home between different target areas
    # 3. Approach via hover (from above) to avoid collisions

    # Start at home
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/home"},
    {"robot": "pf400", "action": "get_joints"},

    # --- Staging calibration ---
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/staging_hover"},
    {"robot": "pf400", "action": "get_joints"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/staging"},
    {"robot": "pf400", "action": "get_joints"},
    # Return to hover, then home
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/staging_hover"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/home"},

    # --- Thermocycler calibration ---
    # IMPORTANT: Open lid before approaching!
    {"robot": "thermocycler", "action": "open"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/thermocycler_nest_hover"},
    {"robot": "pf400", "action": "get_joints"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/thermocycler_nest"},
    {"robot": "pf400", "action": "get_joints"},
    # Return to hover, then home, then close lid
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/thermocycler_nest_hover"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/home"},
    {"robot": "thermocycler", "action": "close"},

    # --- Peeler calibration ---
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/peeler_nest_hover"},
    {"robot": "pf400", "action": "get_joints"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/peeler_nest"},
    {"robot": "pf400", "action": "get_joints"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/peeler_nest_hover"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": f"/World/env_{ENV_ID}/locations/home"},
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

# Robots that support get_status for polling motion completion
# Other robots use simple time-based waiting
ROBOTS_WITH_STATUS = {"pf400"}

# Fixed wait time for robots without status polling (seconds)
SIMPLE_WAIT_TIME = 3.0


class CommandRunner:
    """Executes commands against Isaac Sim ZMQ ROUTER server."""

    def __init__(self, zmq_url: str, env_id: int, stop_on_error: bool = True):
        self.zmq_url = zmq_url
        self.env_id = env_id
        self.stop_on_error = stop_on_error
        self.context = zmq.Context()
        self.sockets = {}  # robot_type -> socket

    def connect(self, robot_type: str):
        """Connect to ROUTER server with robot-specific identity."""
        if robot_type in self.sockets:
            return

        identity = f"env_{self.env_id}.{robot_type}"
        socket = self.context.socket(zmq.DEALER)
        socket.setsockopt_string(zmq.IDENTITY, identity)
        socket.connect(self.zmq_url)
        self.sockets[robot_type] = socket
        print(f"Connected as {identity}")

    def cleanup(self):
        """Close all connections."""
        for socket in self.sockets.values():
            socket.close()
        self.context.term()

    def send_command(self, robot_type: str, command: dict, timeout_ms: int = 5000) -> dict:
        """Send command via DEALER and return response."""
        self.connect(robot_type)
        socket = self.sockets[robot_type]

        try:
            # DEALER sends: [empty, message]
            socket.send_multipart([b"", json.dumps(command).encode()])

            if socket.poll(timeout_ms):
                # DEALER receives: [empty, response]
                _, response_bytes = socket.recv_multipart()
                return json.loads(response_bytes.decode())
            else:
                return {"status": "error", "message": "Timeout waiting for response"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_status(self, robot_type: str) -> dict:
        """Get robot status."""
        return self.send_command(robot_type, {"action": "get_status"})

    def wait_for_completion(self, robot_type: str, max_wait: float = 60.0) -> tuple[bool, str]:
        """Wait for robot motion to complete. Returns (success, message)."""
        start = time.time()
        while time.time() - start < max_wait:
            response = self.get_status(robot_type)

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
        all_success = True

        try:
            for i, cmd in enumerate(commands):
                robot_type = cmd.get("robot")
                action = cmd.get("action")

                if not robot_type or not action:
                    print(f"[{i+1}/{len(commands)}] ERROR: Command missing 'robot' or 'action': {cmd}")
                    if self.stop_on_error:
                        return False
                    all_success = False
                    continue

                # Build the ZMQ command (everything except 'robot' key)
                zmq_cmd = {k: v for k, v in cmd.items() if k != "robot"}

                print(f"[{i+1}/{len(commands)}] env_{self.env_id}.{robot_type}: {action}", end="", flush=True)

                # Send command
                response = self.send_command(robot_type, zmq_cmd)

                if response.get("status") != "success":
                    print(f" -> FAILED: {response.get('message', 'Unknown error')}")
                    if self.stop_on_error:
                        return False
                    all_success = False
                    continue

                # For motion actions, wait for completion
                if action in MOTION_ACTIONS:
                    print(" -> queued, waiting...", end="", flush=True)
                    # Use status polling for robots that support it, time-based for others
                    if robot_type in ROBOTS_WITH_STATUS:
                        success, msg = self.wait_for_completion(robot_type)
                    else:
                        # Simple time-based wait for devices without status polling
                        time.sleep(SIMPLE_WAIT_TIME)
                        success, msg = True, "Motion complete (timed wait)"
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
                    # Format joint angles nicely if present (at top level of response)
                    if "joint_angles" in response:
                        joints = response["joint_angles"]
                        # Round for readability
                        joints_rounded = [round(j, 5) for j in joints]
                        print(f"    Joint angles: {joints_rounded}")

        finally:
            self.cleanup()

        return all_success


def main():
    if not COMMANDS:
        print("No commands defined. Edit the COMMANDS list in this script.")
        sys.exit(1)

    print(f"Executing {len(COMMANDS)} commands for env_{ENV_ID} (stop_on_error={STOP_ON_ERROR})")
    print(f"ZMQ ROUTER: {ZMQ_SERVER_URL}")
    print("-" * 60)

    runner = CommandRunner(ZMQ_SERVER_URL, ENV_ID, stop_on_error=STOP_ON_ERROR)
    success = runner.execute(COMMANDS)

    print("-" * 60)
    if success:
        print("All commands completed successfully")
    else:
        print("Some commands failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
