#!/usr/bin/env python3
"""
PRISM PCR Workflow - Direct Isaac Sim Commands (Joint-based)

Uses DEALER sockets with identity-based routing to communicate with Isaac Sim.
All movements use move_joints with original joint angles from location.manager.yaml.
Home reset before any motion to sealer, thermocycler, peeler, or hidex.
"""

import json
import sys
import time

import zmq


# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment ID (use 0 for single-environment setups)
ENV_ID = 0

# ZMQ ROUTER server (single multiplexed port)
ZMQ_SERVER_URL = "tcp://localhost:5555"

STOP_ON_ERROR = True

# Home position joint angles
HOME_JOINTS = [-0.263, 0.362, 0, 0, 0, 0, 0]

# ============================================================================
# JOINT ANGLES (from location.manager.yaml)
# ============================================================================

JOINTS = {
    # OT-2 locations
    "ot2bioalpha_deck1_wide": [0.38454803824424744, 0.14513998210430146, 0.1898307353258133, 1.4468275308609009, -3.2075114250183105, 0.0, 0],
    "safe_path_ot2bioalpha": [0.5400072336196899, 0.3368925869464874, 0, 0, 0, 0, 0],
    # Exchange locations
    "exchange_deck_high_wide": [0.6705737709999084, 0.13769488036632538, 1.1280133724212646, -0.6996639370918274, 1.1419706344604492, 0, 0],
    "exchange_deck_high_narrow": [0.4321829080581665, 0.13769488036632538, 0.7130301594734192, -1.075421690940857, 0.36238372325897217, 0, 0],
    "safe_path_exchange": [0.4321829080581665, 0.4368929922580719, 0.7130301594734192, -1.075421690940857, 0.36238375306129456, 0, 0],
    # Sealer locations
    "sealer_nest": [-0.40044429898262024, 0.14, 0.400662362575531, 1.4502944946289062, -3.4217817783355713, 0, 0],
    "safe_path_sealer": [-0.40040111541748047, 0.4108368158340454, 0.4006734788417816, 1.4502149820327759, -3.4218459129333496, 0, 0],
    # Thermocycler locations
    "bio_biometra3_nest": [-0.14252401888370514, 0.1632107889652252, -0.10332811623811722, -1.1150076389312744, 2.7891077995300293, 0, 0],
    "safe_path_biometra3": [-0.14252401888370514, 0.45315250754356384, -0.10332823544740677, -1.1150076389312744, 2.7891077995300293, 0.0, 0],
    # Peeler locations
    "peeler_nest": [-0.7275359630584717, 0.16, 0.2995404601097107, 1.450539469718933, -3.32090425491333, 0, 0],
    "safe_path_peeler": [-0.7274733781814575, 0.4308168292045593, 0.29955071210861206, 1.4504271745681763, -3.321009874343872, 0, 0],
    # Hidex locations
    "hidex_geraldine_high_nest": [-0.7823303937911987, 0.07264269143342972, -0.7316455841064453, -1.0245424509048462, 3.327012777328491, 0, 0],
    "safe_path_hidex": [-0.5422155261039734, 0.2716383635997772, 0, 0, 0, 0, 0],
}


def hover(joints, height=0.1):
    """Create hover position by adding height to joint index 1."""
    result = list(joints)
    result[1] = result[1] + height
    return result


def transfer(source, source_approach, target, target_approach):
    """Generate transfer commands using move_joints."""
    src = JOINTS[source]
    src_approach = JOINTS[source_approach]
    tgt = JOINTS[target]
    tgt_approach = JOINTS[target_approach]

    cmds = []
    # Pick
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": src_approach, "_comment": f"Approach {source_approach}"})
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": hover(src), "_comment": f"Hover above {source}"})
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": src, "_comment": f"Lower to {source}"})
    cmds.append({"robot": "pf400", "action": "gripper_close", "_comment": "Pick up plate"})
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": hover(src), "_comment": f"Retract from {source}"})
    # Place
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": tgt_approach, "_comment": f"Approach {target_approach}"})
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": hover(tgt), "_comment": f"Hover above {target}"})
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": tgt, "_comment": f"Lower to {target}"})
    cmds.append({"robot": "pf400", "action": "gripper_open", "_comment": "Release plate"})
    cmds.append({"robot": "pf400", "action": "move_joints", "joint_positions": hover(tgt), "_comment": f"Retract from {target}"})
    return cmds


def home():
    """Return home command."""
    return {"robot": "pf400", "action": "move_joints", "joint_positions": HOME_JOINTS, "_comment": "Home"}


# ============================================================================
# COMMAND SEQUENCE
# ============================================================================

COMMANDS = []

# Initialize: Go to home
COMMANDS.append({"_step": "Initialize: Go to home"})
COMMANDS.append(home())

# Transfer: OT-2 -> Exchange (wide)
COMMANDS.append({"_step": "Transfer: OT-2 -> Exchange (wide)"})
COMMANDS.extend(transfer("ot2bioalpha_deck1_wide", "safe_path_ot2bioalpha", "exchange_deck_high_wide", "safe_path_exchange"))

# Home before sealer
COMMANDS.append({"_step": "Home before sealer"})
COMMANDS.append(home())

# Transfer: Exchange -> Sealer (narrow)
COMMANDS.append({"_step": "Transfer: Exchange -> Sealer (narrow)"})
COMMANDS.extend(transfer("exchange_deck_high_narrow", "safe_path_exchange", "sealer_nest", "safe_path_sealer"))

# Seal
COMMANDS.append({"_step": "Seal plate"})
COMMANDS.append({"robot": "sealer", "action": "seal"})

# Home before thermocycler
COMMANDS.append({"_step": "Home before thermocycler open"})
COMMANDS.append(home())

# Open thermocycler
COMMANDS.append({"_step": "Open thermocycler"})
COMMANDS.append({"robot": "thermocycler", "action": "open"})

# Home before sealer pickup
COMMANDS.append({"_step": "Home before sealer pickup"})
COMMANDS.append(home())

# Transfer: Sealer -> Exchange (narrow)
COMMANDS.append({"_step": "Transfer: Sealer -> Exchange (narrow)"})
COMMANDS.extend(transfer("sealer_nest", "safe_path_sealer", "exchange_deck_high_narrow", "safe_path_exchange"))

# Home before thermocycler
COMMANDS.append({"_step": "Home before thermocycler"})
COMMANDS.append(home())

# Transfer: Exchange -> Thermocycler (wide)
COMMANDS.append({"_step": "Transfer: Exchange -> Thermocycler (wide)"})
COMMANDS.extend(transfer("exchange_deck_high_wide", "safe_path_exchange", "bio_biometra3_nest", "safe_path_biometra3"))

# Close thermocycler
COMMANDS.append({"_step": "Close thermocycler"})
COMMANDS.append({"robot": "thermocycler", "action": "close"})

# Run thermocycler
COMMANDS.append({"_step": "Run thermocycler program"})
COMMANDS.append({"robot": "thermocycler", "action": "run_program", "program_number": 5})

# Open thermocycler
COMMANDS.append({"_step": "Open thermocycler (unload)"})
COMMANDS.append({"robot": "thermocycler", "action": "open"})

# Home before thermocycler pickup
COMMANDS.append({"_step": "Home before thermocycler pickup"})
COMMANDS.append(home())

# Transfer: Thermocycler -> Exchange (wide)
COMMANDS.append({"_step": "Transfer: Thermocycler -> Exchange (wide)"})
COMMANDS.extend(transfer("bio_biometra3_nest", "safe_path_biometra3", "exchange_deck_high_wide", "safe_path_exchange"))

# Home before peeler
COMMANDS.append({"_step": "Home before peeler"})
COMMANDS.append(home())

# Transfer: Exchange -> Peeler (narrow)
COMMANDS.append({"_step": "Transfer: Exchange -> Peeler (narrow)"})
COMMANDS.extend(transfer("exchange_deck_high_narrow", "safe_path_exchange", "peeler_nest", "safe_path_peeler"))

# Peel
COMMANDS.append({"_step": "Peel plate"})
COMMANDS.append({"robot": "peeler", "action": "peel"})

# Home before hidex
COMMANDS.append({"_step": "Home before hidex"})
COMMANDS.append(home())

# Open Hidex
COMMANDS.append({"_step": "Open Hidex"})
COMMANDS.append({"robot": "hidex", "action": "open"})

# Home before peeler pickup
COMMANDS.append({"_step": "Home before peeler pickup"})
COMMANDS.append(home())

# Transfer: Peeler -> Hidex (narrow)
COMMANDS.append({"_step": "Transfer: Peeler -> Hidex (narrow)"})
COMMANDS.extend(transfer("peeler_nest", "safe_path_peeler", "hidex_geraldine_high_nest", "safe_path_hidex"))

# Close Hidex
COMMANDS.append({"_step": "Close Hidex"})
COMMANDS.append({"robot": "hidex", "action": "close"})

# Run assay
COMMANDS.append({"_step": "Run Hidex assay"})
COMMANDS.append({"robot": "hidex", "action": "run_assay", "assay_name": "PCR_Final_Results"})

# Open Hidex
COMMANDS.append({"_step": "Open Hidex (complete)"})
COMMANDS.append({"robot": "hidex", "action": "open"})


# ============================================================================
# RUNNER CODE
# ============================================================================

MOTION_ACTIONS = {"move_joints", "goto_pose", "goto_prim", "gripper_open", "gripper_close"}

# Robots that support get_status for polling motion completion
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

    def send_command(self, robot_type: str, cmd: dict, timeout_ms: int = 5000) -> dict:
        """Send command via DEALER and return response."""
        self.connect(robot_type)
        socket = self.sockets[robot_type]

        try:
            # DEALER sends: [empty, message]
            socket.send_multipart([b"", json.dumps(cmd).encode()])

            if socket.poll(timeout_ms):
                # DEALER receives: [empty, response]
                _, response_bytes = socket.recv_multipart()
                return json.loads(response_bytes.decode())
            else:
                return {"status": "error", "message": "Timeout"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def wait_for_completion(self, robot_type: str, max_wait: float = 60.0) -> tuple[bool, str]:
        """Wait for robot motion to complete. Returns (success, message)."""
        start = time.time()
        while time.time() - start < max_wait:
            resp = self.send_command(robot_type, {"action": "get_status"})
            if resp.get("status") != "success":
                return False, f"Status error: {resp.get('message')}"
            data = resp.get("data", {})
            if data.get("collision_detected"):
                return False, "Collision detected"
            if data.get("motion_complete") and not data.get("is_moving"):
                return True, "OK"
            time.sleep(0.05)
        return False, f"Timeout after {max_wait}s"

    def execute(self, commands: list) -> bool:
        """Execute command sequence. Returns True if all succeeded."""
        cmd_num = 0
        try:
            for cmd in commands:
                if "_step" in cmd:
                    print(f"\n{'='*60}\n  {cmd['_step']}\n{'='*60}")
                    continue

                robot_type = cmd.get("robot")
                action = cmd.get("action")
                if not robot_type or not action:
                    continue

                cmd_num += 1
                comment = cmd.get("_comment", action)
                zmq_cmd = {k: v for k, v in cmd.items() if not k.startswith("_") and k != "robot"}

                print(f"  [{cmd_num}] env_{self.env_id}.{robot_type}: {comment}", end="", flush=True)

                resp = self.send_command(robot_type, zmq_cmd)
                if resp.get("status") != "success":
                    print(f" -> FAILED: {resp.get('message')}")
                    if self.stop_on_error:
                        return False
                    continue

                if action in MOTION_ACTIONS:
                    # Use status polling for robots that support it, time-based for others
                    if robot_type in ROBOTS_WITH_STATUS:
                        ok, msg = self.wait_for_completion(robot_type)
                    else:
                        time.sleep(SIMPLE_WAIT_TIME)
                        ok, msg = True, "OK (timed wait)"
                    print(f" -> {msg}")
                    if not ok and self.stop_on_error:
                        return False
                else:
                    print(" -> OK")

        finally:
            self.cleanup()
        return True


def main():
    actual = [c for c in COMMANDS if "robot" in c]
    print(f"PRISM PCR Workflow - {len(actual)} commands")
    print(f"ZMQ ROUTER: {ZMQ_SERVER_URL}")
    print("-" * 60)

    runner = CommandRunner(ZMQ_SERVER_URL, ENV_ID, STOP_ON_ERROR)
    success = runner.execute(COMMANDS)

    print("\n" + "="*60)
    print("Workflow completed successfully" if success else "Workflow failed")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
