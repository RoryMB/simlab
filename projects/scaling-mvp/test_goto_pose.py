#!/usr/bin/env python3
"""Test script for differential IK goto_pose command.

This script tests the PF400's differential IK implementation by:
1. Getting the current end effector pose
2. Sending a goto_pose command with a slightly offset target
3. Waiting for motion to complete
4. Verifying the robot moved to the target

Usage:
    python test_goto_pose.py

Requires Isaac Sim to be running with the PF400 robot loaded.
"""

import json
import time

import zmq


def create_zmq_client(server_url: str = "tcp://localhost:5555", identity: str = "env_0.pf400"):
    """Create a ZMQ DEALER client."""
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt_string(zmq.IDENTITY, identity)
    socket.connect(server_url)
    return context, socket


def send_command(socket, command: dict, timeout_ms: int = 10000) -> dict:
    """Send a ZMQ command and wait for response."""
    socket.send_multipart([b"", json.dumps(command).encode()])
    if socket.poll(timeout_ms):
        _, response_bytes = socket.recv_multipart()
        return json.loads(response_bytes.decode())
    else:
        return {"status": "error", "message": f"Timeout after {timeout_ms}ms"}


def wait_for_motion_complete(socket, max_wait: float = 30.0) -> bool:
    """Wait for robot motion to complete."""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status = send_command(socket, {"action": "get_status"})
        if status.get("status") != "success":
            print(f"Failed to get status: {status}")
            return False

        data = status.get("data", {})
        if data.get("collision_detected", False):
            print("Motion stopped due to collision")
            return False

        if data.get("motion_complete", False) or not data.get("is_moving", False):
            print("Motion completed successfully")
            return True

        time.sleep(0.1)

    print(f"Motion did not complete within {max_wait} seconds")
    return False


def main():
    print("=" * 60)
    print("Testing Differential IK - goto_pose command")
    print("=" * 60)

    # Connect to ZMQ server
    print("\nConnecting to ZMQ server...")
    context, socket = create_zmq_client()
    print("Connected as 'env_0.pf400'")

    try:
        # Step 1: Get current end effector pose
        print("\n--- Step 1: Get current end effector pose ---")
        response = send_command(socket, {"action": "get_ee_pose"})
        if response.get("status") != "success":
            print(f"Failed to get EE pose: {response}")
            return 1

        ee_data = response.get("data", {})
        current_position = ee_data.get("position", [])
        current_orientation = ee_data.get("orientation", [])
        print(f"Current EE position: {current_position}")
        print(f"Current EE orientation: {current_orientation}")

        if not current_position or not current_orientation:
            print("Invalid EE pose data")
            return 1

        # Step 2: Create target pose with offset
        print("\n--- Step 2: Create target pose ---")
        # Move 1cm in the Z direction from current position
        target_position = [
            current_position[0],
            current_position[1],
            current_position[2] + 0.01,  # 1cm in Z (up)
        ]
        target_orientation = current_orientation  # Keep same orientation

        print(f"Target position: {target_position}")
        print(f"Target orientation: {target_orientation}")

        # Step 3: Send goto_pose command
        print("\n--- Step 3: Send goto_pose command ---")
        response = send_command(socket, {
            "action": "goto_pose",
            "position": target_position,
            "orientation": target_orientation,
        })
        print(f"Response: {response}")

        if response.get("status") != "success":
            print(f"goto_pose command failed: {response}")
            return 1

        # Step 4: Wait for motion to complete
        print("\n--- Step 4: Wait for motion to complete ---")
        if not wait_for_motion_complete(socket):
            print("Motion did not complete successfully")
            return 1

        # Step 5: Verify final position
        print("\n--- Step 5: Verify final position ---")
        response = send_command(socket, {"action": "get_ee_pose"})
        if response.get("status") != "success":
            print(f"Failed to get final EE pose: {response}")
            return 1

        ee_data = response.get("data", {})
        final_position = ee_data.get("position", [])
        final_orientation = ee_data.get("orientation", [])
        print(f"Final EE position: {final_position}")
        print(f"Final EE orientation: {final_orientation}")

        # Calculate position error
        position_error = [
            abs(final_position[i] - target_position[i])
            for i in range(3)
        ]
        total_error = sum(position_error)
        print(f"Position error: {position_error}")
        print(f"Total position error: {total_error:.6f} m")

        if total_error < 0.01:  # 10mm tolerance (differential IK does one step)
            print("\nSUCCESS: Robot reached target within tolerance")
            return 0
        else:
            print(f"\nWARNING: Robot position error ({total_error:.6f}m) exceeds tolerance (0.01m)")
            return 1

    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    exit(main())
