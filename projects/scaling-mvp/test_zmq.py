#!/usr/bin/env python
"""Test ZMQ communication with Isaac Sim ROUTER server."""

import json
import sys
import zmq

def test_zmq(env_id: int = 0, robot_type: str = "thermocycler", action: str = "open"):
    """Send a test command to verify ZMQ communication."""
    identity = f"env_{env_id}.{robot_type}"
    server_url = "tcp://localhost:5555"

    print(f"Testing ZMQ communication:")
    print(f"  Identity: {identity}")
    print(f"  Server: {server_url}")
    print(f"  Action: {action}")
    print()

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt_string(zmq.IDENTITY, identity)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.connect(server_url)

    command = {"action": action}
    print(f"Sending: {command}")

    # DEALER sends: [empty, message]
    socket.send_multipart([b"", json.dumps(command).encode()])

    print("Waiting for response...")
    try:
        # DEALER receives: [empty, response]
        _, response_bytes = socket.recv_multipart()
        response = json.loads(response_bytes.decode())
        print(f"Response: {json.dumps(response, indent=2)}")
    except zmq.Again:
        print("ERROR: Timeout waiting for response from Isaac Sim")
        print("  - Is Isaac Sim running with run.py?")
        print("  - Check Isaac Sim terminal for errors")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    env_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    robot_type = sys.argv[2] if len(sys.argv) > 2 else "thermocycler"
    action = sys.argv[3] if len(sys.argv) > 3 else "open"
    test_zmq(env_id, robot_type, action)
