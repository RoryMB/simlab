#!/usr/bin/env python3
"""Simple test to verify PF400 ZMQ connection"""

import json
import zmq
import sys

def test_pf400_connection():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5557")
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        # Send a simple status command
        command = {"action": "get_status"}
        socket.send_string(json.dumps(command))
        
        # Receive response
        response_str = socket.recv_string()
        response = json.loads(response_str)
        
        print("✅ PF400 Connection Test:")
        print(f"   Status: {response.get('status')}")
        print(f"   Joint angles: {response.get('joint_angles', 'N/A')}")
        print(f"   Gripper state: {response.get('gripper_state', 'N/A')}")
        print(f"   Moving: {response.get('is_moving', 'N/A')}")
        
        return response.get("status") == "success"
        
    except zmq.Again:
        print("❌ Timeout - PF400 not responding")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_pf400_connection()