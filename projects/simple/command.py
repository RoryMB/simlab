#!/usr/bin/env python3
"""Direct ZMQ command script for the simple project.

Talks directly to Isaac Sim via ZMQ, bypassing MADSci entirely.
Useful for testing robot communication and calibrating positions.

Usage:
    1. Start Isaac Sim: python run_sim.py
    2. Edit COMMANDS below
    3. Run: python command.py
"""

import json
import sys
import time

import zmq


# ============================================================================
# CONFIGURATION - Edit this section
# ============================================================================

ZMQ_SERVER_URL = "tcp://localhost:5555"

# Commands to execute sequentially.
# Each command needs "robot" (pf400, thermocycler, or peeler) and "action".
COMMANDS = [
    # Move PF400 to home
    {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/home"},

    # Open thermocycler, move PF400 above it, then return home
    {"robot": "thermocycler", "action": "open"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/thermocycler_nest_hover"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/home"},
    {"robot": "thermocycler", "action": "close"},

    # Move PF400 to peeler area and back
    {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/peeler_nest_hover"},
    {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/home"},

    # --- Other available commands (uncomment to use) ---
    # {"robot": "pf400", "action": "get_joints"},
    # {"robot": "pf400", "action": "get_status"},
    # {"robot": "pf400", "action": "goto_prim", "prim_name": "/World/env_0/locations/staging"},
    # {"robot": "pf400", "action": "move_joints", "joint_angles": [0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0]},
    # {"robot": "pf400", "action": "gripper_open"},
    # {"robot": "pf400", "action": "gripper_close"},
    # {"robot": "peeler", "action": "peel"},
]


# ============================================================================
# RUNNER CODE - No need to edit below this line
# ============================================================================

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

ROBOTS_WITH_STATUS = {"pf400"}
SIMPLE_WAIT_TIME = 3.0


def send_command(socket, command: dict, timeout_ms: int = 5000) -> dict:
    """Send command via DEALER and return response."""
    socket.send_multipart([b"", json.dumps(command).encode()])
    if socket.poll(timeout_ms):
        _, response_bytes = socket.recv_multipart()
        return json.loads(response_bytes.decode())
    return {"status": "error", "message": "Timeout waiting for response"}


def wait_for_completion(socket, max_wait: float = 60.0) -> tuple[bool, str]:
    """Wait for PF400 motion to complete by polling status."""
    start = time.time()
    while time.time() - start < max_wait:
        response = send_command(socket, {"action": "get_status"})
        if response.get("status") != "success":
            return False, f"Status check failed: {response.get('message', 'Unknown error')}"
        data = response.get("data", {})
        if data.get("collision_detected", False):
            return False, "Collision detected"
        if data.get("motion_complete", True) and not data.get("is_moving", False):
            return True, "Motion complete"
        time.sleep(0.05)
    return False, f"Timeout after {max_wait}s"


def main():
    if not COMMANDS:
        print("No commands defined. Edit the COMMANDS list in this script.")
        sys.exit(1)

    print(f"Executing {len(COMMANDS)} commands")
    print(f"ZMQ ROUTER: {ZMQ_SERVER_URL}")
    print("-" * 60)

    context = zmq.Context()
    sockets = {}  # robot_type -> socket

    try:
        for i, cmd in enumerate(COMMANDS):
            robot_type = cmd["robot"]
            action = cmd["action"]

            # Connect socket for this robot type if needed
            if robot_type not in sockets:
                identity = f"env_0.{robot_type}"
                socket = context.socket(zmq.DEALER)
                socket.setsockopt_string(zmq.IDENTITY, identity)
                socket.connect(ZMQ_SERVER_URL)
                sockets[robot_type] = socket
                print(f"Connected as {identity}")

            socket = sockets[robot_type]
            zmq_cmd = {k: v for k, v in cmd.items() if k != "robot"}

            print(f"[{i+1}/{len(COMMANDS)}] {robot_type}: {action}", end="", flush=True)

            response = send_command(socket, zmq_cmd)

            if response.get("status") != "success":
                print(f" -> FAILED: {response.get('message', 'Unknown error')}")
                sys.exit(1)

            if action in MOTION_ACTIONS:
                print(" -> waiting...", end="", flush=True)
                if robot_type in ROBOTS_WITH_STATUS:
                    success, msg = wait_for_completion(socket)
                else:
                    time.sleep(SIMPLE_WAIT_TIME)
                    success, msg = True, "Done (timed wait)"
                print(f" -> {msg}")
                if not success:
                    sys.exit(1)
            else:
                print(" -> OK")
                if "joint_angles" in response:
                    joints = [round(j, 5) for j in response["joint_angles"]]
                    print(f"    Joint angles: {joints}")

    finally:
        for s in sockets.values():
            s.close()
        context.term()

    print("-" * 60)
    print("All commands completed successfully")


if __name__ == "__main__":
    main()
