from isaacsim import SimulationApp

# This MUST be run before importing ANYTHING else
simulation_app = SimulationApp({"headless": False})

import json
import sys
import threading

import numpy as np
import zmq

import utils
from isaacsim.core.api import World
from isaacsim.core.api.robots import Robot
from isaacsim.core.utils.rotations import quat_to_euler_angles
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path


CUSTOM_ASSETS_ROOT_PATH = "../../assets"

NVIDIA_ASSETS_ROOT_PATH = get_assets_root_path()
if NVIDIA_ASSETS_ROOT_PATH is None:
    print("Error: Could not find Isaac Sim assets folder")
    simulation_app.close()
    sys.exit()


class ZMQRobotServer:
    """Handles ZMQ communication for a single robot"""
    def __init__(self, robot, robot_name: str, port: int):
        self.robot = robot  # Isaac Sim Robot object from world.scene.add(Robot(...))
        self.robot_name = robot_name
        self.port = port
        self.context = None
        self.socket = None

    def start_server(self):
        """Start ZMQ server in background thread"""
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()
        return zmq_thread

    def zmq_server_thread(self):
        """ZMQ server running in background thread"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")

        while simulation_app.is_running():
            try:
                # Receive request with timeout
                if self.socket.poll(100):  # 100ms timeout
                    message = self.socket.recv_string(zmq.NOBLOCK)
                    request = json.loads(message)

                    # Handle command
                    response = self.handle_command(request)

                    # Send response
                    self.socket.send_string(json.dumps(response))

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ZMQ server error for {self.robot_name}: {e}")
                error_response = {"status": "error", "message": str(e)}
                self.socket.send_string(json.dumps(error_response))

        self.socket.close()
        self.context.term()

    def handle_command(self, request):
        """Handle incoming ZMQ command from MADSci"""
        action = request.get("action", "")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])
            print(f"Received command for {self.robot_name}: Move robot to joint angles: {joint_angles}")

            if len(joint_angles) != 6:
                return {"status": "error", "message": f"Expected 6 joint angles, got {len(joint_angles)}"}

            try:
                self.robot.set_joint_positions(np.array(joint_angles))
                return {"status": "success", "message": "moved", "joint_angles": joint_angles}
            except Exception as e:
                return {"status": "error", "message": f"Failed to move robot: {str(e)}"}

        elif action == "get_joints":
            print(f"Received command for {self.robot_name}: Get robot joint angles")

            try:
                joint_positions = self.robot.get_joint_positions()
                return {"status": "success", "joint_angles": joint_positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

        elif action == "get_pose":
            print(f"Received command for {self.robot_name}: Get robot end effector pose")

            try:
                joint_positions = self.robot.get_joint_positions()

                # Calculate forward kinematics using utils
                ee_pos, ee_orient = utils.get_robot_end_effector_pose(self.robot)
                # Convert quaternion (w,x,y,z) to euler angles using Isaac Sim utilities
                euler = quat_to_euler_angles(ee_orient)
                pose = [ee_pos[0], ee_pos[1], ee_pos[2], euler[0], euler[1], euler[2]]
                print(f"FK calculated pose: position={ee_pos}, orientation={ee_orient}")

                return {"status": "success", "pose": pose, "joint_angles": joint_positions.tolist()}
            except Exception as e:
                return {"status": "error", "message": f"Failed to get pose: {str(e)}"}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}


class ZMQOT2RobotServer:
    """Handles ZMQ communication for OT-2 robot with opentrons-specific commands"""
    def __init__(self, robot, robot_name: str, port: int):
        self.robot = robot  # Isaac Sim Robot object
        self.robot_name = robot_name
        self.port = port
        self.context = None
        self.socket = None

        # OT-2 joint mapping (joint index -> joint name)
        self.joint_names = [
            "pipette_rail_joint",      # 0: Y-axis (front/back)
            "pipette_casing_joint",    # 1: X-axis (left/right)
            "pipette_left_joint",      # 2: Left Z (up/down)
            "pipette_right_joint",     # 3: Right Z (up/down)
            "left_plunger_joint",      # 4: Left plunger
            "right_plunger_joint",     # 5: Right plunger
            "left_tip_ejector_joint",  # 6: Left tip ejector
            "right_tip_ejector_joint", # 7: Right tip ejector
        ]

        # Joint limits (from test_ot2_server.py)
        self.joint_limits = {
            "pipette_rail_joint": (0.0, 0.353),
            "pipette_casing_joint": (0.0, 0.418),
            "pipette_left_joint": (-0.218, 0.0),
            "pipette_right_joint": (-0.218, 0.0),
            "left_plunger_joint": (0.0, 0.019),
            "right_plunger_joint": (0.0, 0.019),
            "left_tip_ejector_joint": (0.0, 0.005),
            "right_tip_ejector_joint": (0.0, 0.005),
        }

        # Home positions
        self.home_positions = {
            "pipette_rail_joint": 0.353,      # Y-axis home (back)
            "pipette_casing_joint": 0.418,    # X-axis home (right)
            "pipette_left_joint": 0.0,        # Left Z home (top)
            "pipette_right_joint": 0.0,       # Right Z home (top)
            "left_plunger_joint": 0.0,        # Left plunger home
            "right_plunger_joint": 0.0,       # Right plunger home
            "left_tip_ejector_joint": 0.0,    # Left tip ejector retracted
            "right_tip_ejector_joint": 0.0,   # Right tip ejector retracted
        }

        # Tip attachment state
        self.left_tip_attached = False
        self.right_tip_attached = False

    def start_server(self):
        """Start ZMQ server in background thread"""
        zmq_thread = threading.Thread(target=self.zmq_server_thread, daemon=True)
        zmq_thread.start()
        return zmq_thread

    def zmq_server_thread(self):
        """ZMQ server running in background thread"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")

        print(f"OT-2 ZMQ server listening on port {self.port}")

        while simulation_app.is_running():
            try:
                if self.socket.poll(100):  # 100ms timeout
                    message = self.socket.recv_string(zmq.NOBLOCK)
                    request = json.loads(message)

                    print(f"OT-2 received command: {request}")

                    # Handle command
                    response = self.handle_command(request)

                    print(f"OT-2 sending response: {response}")

                    # Send response
                    self.socket.send_string(json.dumps(response))

            except zmq.Again:
                continue
            except Exception as e:
                print(f"ZMQ server error for {self.robot_name}: {e}")
                error_response = {"status": "error", "message": str(e)}
                self.socket.send_string(json.dumps(error_response))

        self.socket.close()
        self.context.term()

    def handle_command(self, request):
        """Handle incoming ZMQ command from opentrons package"""
        action = request.get("action", "")

        if action == "move_joint":
            joint_name = request.get("joint")
            target_position = request.get("target_position")

            if joint_name and target_position is not None:
                return self.move_single_joint(joint_name, target_position)
            else:
                return {"status": "error", "message": "Missing joint name or target position"}

        elif action == "move_joints":
            joint_commands = request.get("joint_commands", [])

            if joint_commands:
                return self.move_multiple_joints(joint_commands)
            else:
                return {"status": "error", "message": "No joint commands provided"}

        elif action == "get_joints":
            return self.get_joint_positions()

        elif action == "get_status":
            return self.get_robot_status()

        elif action == "home":
            return self.home_robot()

        elif action == "pick_up_tip":
            mount = request.get("mount", "left")
            return self.pick_up_tip(mount)

        elif action == "drop_tip":
            mount = request.get("mount", "left")
            return self.drop_tip(mount)

        elif action == "aspirate":
            mount = request.get("mount", "left")
            volume = request.get("volume", 0.0)
            return self.aspirate(mount, volume)

        elif action == "dispense":
            mount = request.get("mount", "left")
            volume = request.get("volume", 0.0)
            return self.dispense(mount, volume)

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def move_single_joint(self, joint_name: str, target_position: float):
        """Move a single joint to target position"""
        if joint_name not in self.joint_names:
            return {"status": "error", "message": f"Unknown joint: {joint_name}"}

        # Check limits
        min_pos, max_pos = self.joint_limits[joint_name]
        if target_position < min_pos or target_position > max_pos:
            return {"status": "error", "message": f"Target position {target_position} out of bounds for {joint_name} [{min_pos}, {max_pos}]"}

        try:
            # Get current joint positions
            current_positions = self.robot.get_joint_positions()
            joint_index = self.joint_names.index(joint_name)

            # Update the specific joint
            new_positions = current_positions.copy()
            new_positions[joint_index] = target_position

            # Apply to robot
            self.robot.set_joint_positions(new_positions)

            return {
                "status": "success",
                "message": f"Moving {joint_name} to {target_position}m",
                "joint": joint_name,
                "target_position": target_position
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to move joint: {str(e)}"}

    def move_multiple_joints(self, joint_commands):
        """Move multiple joints simultaneously"""
        try:
            current_positions = self.robot.get_joint_positions()
            new_positions = current_positions.copy()

            # Validate and prepare all commands
            for cmd in joint_commands:
                joint_name = cmd.get("joint")
                target_position = cmd.get("target_position")

                if joint_name not in self.joint_names:
                    return {"status": "error", "message": f"Unknown joint: {joint_name}"}

                min_pos, max_pos = self.joint_limits[joint_name]
                if target_position < min_pos or target_position > max_pos:
                    return {"status": "error", "message": f"Target position {target_position} out of bounds for {joint_name}"}

                joint_index = self.joint_names.index(joint_name)
                new_positions[joint_index] = target_position

            # Apply all movements
            self.robot.set_joint_positions(new_positions)

            return {
                "status": "success",
                "message": f"Moving {len(joint_commands)} joints",
                "joint_commands": joint_commands
            }

        except Exception as e:
            return {"status": "error", "message": f"Failed to move joints: {str(e)}"}

    def get_joint_positions(self):
        """Get current joint positions"""
        try:
            positions = self.robot.get_joint_positions()
            joint_positions = {}
            for i, joint_name in enumerate(self.joint_names):
                joint_positions[joint_name] = positions[i] if i < len(positions) else 0.0

            return {"status": "success", "joint_positions": joint_positions}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get joint positions: {str(e)}"}

    def get_robot_status(self):
        """Get robot status information"""
        return {
            "status": "success",
            "robot_status": {
                "is_moving": False,  # Could track this in future
                "ready": True,
                "joint_count": len(self.joint_names),
                "left_tip_attached": self.left_tip_attached,
                "right_tip_attached": self.right_tip_attached,
            }
        }

    def home_robot(self):
        """Return all joints to home positions"""
        try:
            home_commands = []
            for joint_name, home_pos in self.home_positions.items():
                home_commands.append({
                    "joint": joint_name,
                    "target_position": home_pos
                })

            return self.move_multiple_joints(home_commands)

        except Exception as e:
            return {"status": "error", "message": f"Failed to home robot: {str(e)}"}

    def pick_up_tip(self, mount: str):
        """Simulate tip pickup"""
        print(f"Simulating tip pickup on {mount} mount")

        if mount == "left":
            self.left_tip_attached = True
        elif mount == "right":
            self.right_tip_attached = True
        else:
            return {"status": "error", "message": f"Invalid mount: {mount}"}

        return {
            "status": "success",
            "message": f"Tip pickup on {mount} mount",
            "mount": mount
        }

    def drop_tip(self, mount: str):
        """Simulate tip drop using ejector"""
        print(f"Simulating tip drop on {mount} mount")

        try:
            if mount == "left":
                # Extend ejector to push tip off
                self.move_single_joint("left_tip_ejector_joint", 0.005)
                # Retract ejector
                self.move_single_joint("left_tip_ejector_joint", 0.0)
                self.left_tip_attached = False
            elif mount == "right":
                self.move_single_joint("right_tip_ejector_joint", 0.005)
                self.move_single_joint("right_tip_ejector_joint", 0.0)
                self.right_tip_attached = False
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

            return {
                "status": "success",
                "message": f"Tip drop on {mount} mount",
                "mount": mount
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to drop tip: {str(e)}"}

    def aspirate(self, mount: str, volume: float):
        """Simulate liquid aspiration"""
        print(f"Simulating aspirate {volume}μL on {mount} mount")

        try:
            # Convert volume to plunger position (simplified linear mapping)
            plunger_position = min(volume / 1000.0 * 0.019, 0.019)  # Max 19mm

            if mount == "left":
                return self.move_single_joint("left_plunger_joint", plunger_position)
            elif mount == "right":
                return self.move_single_joint("right_plunger_joint", plunger_position)
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

        except Exception as e:
            return {"status": "error", "message": f"Failed to aspirate: {str(e)}"}

    def dispense(self, mount: str, volume: float):
        """Simulate liquid dispensing"""
        print(f"Simulating dispense {volume}μL on {mount} mount")

        try:
            # Return plunger to home position for full dispense
            if mount == "left":
                return self.move_single_joint("left_plunger_joint", 0.0)
            elif mount == "right":
                return self.move_single_joint("right_plunger_joint", 0.0)
            else:
                return {"status": "error", "message": f"Invalid mount: {mount}"}

        except Exception as e:
            return {"status": "error", "message": f"Failed to dispense: {str(e)}"}


def create_robots(world, robots_config):
    """Create robots and their ZMQ servers"""
    robots = []
    zmq_servers = []

    for config in robots_config:
        # Create robot in simulation
        add_reference_to_stage(
            usd_path=config["asset_path"],
            prim_path=f"/World/{config['name']}",
        )
        if "position" in config or "orientation" in config:
            robot_prim = world.stage.GetPrimAtPath(f"/World/{config['name']}")

            position = np.array(config.get("position", [0.0, 0.0, 0.0]))
            orientation = np.array(config.get("orientation", [1.0, 0.0, 0.0, 0.0]))

            utils.set_prim_world_pose(robot_prim, position=position, orientation=orientation)

        robot = world.scene.add(Robot(
            prim_path=f"/World/{config['name']}",
            name=config["name"],
        ))

        # Create appropriate ZMQ server based on robot type
        robot_type = config.get("type", "generic")
        if robot_type == "ot2":
            zmq_server = ZMQOT2RobotServer(robot, config["name"], config["port"])
        else:
            # Default to generic robot server (for UR5e, etc.)
            zmq_server = ZMQRobotServer(robot, config["name"], config["port"])

        robots.append(robot)
        zmq_servers.append(zmq_server)

    return robots, zmq_servers


def main():
    # Create world
    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    # Robot configuration
    robots_config = [
        {
            "name": "ur5e_robot",
            "type": "generic",
            "port": 5555,
            "asset_path": NVIDIA_ASSETS_ROOT_PATH + "/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd",
            "position": [2.0, 0.0, 0.0],  # [x, y, z] in world frame
            "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        },
        {
            "name": "ot2_robot",
            "type": "ot2",
            "port": 5556,
            "asset_path": CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/ot2.usda",
            "position": [0.0, 2.0, 0.0],  # [x, y, z] in world frame
            "orientation": [1.0, 0.0, 0.0, 0.0],  # [w, x, y, z] quaternion
        }
    ]

    # Create robots and their ZMQ servers
    robots, zmq_servers = create_robots(world, robots_config)

    # Reset world to initialize physics
    world.reset()

    # Start all ZMQ servers
    for server in zmq_servers:
        server.start_server()

    # Run simulation loop
    try:
        while simulation_app.is_running():
            world.step(render=True)
    except KeyboardInterrupt:
        pass

    simulation_app.close()

if __name__ == "__main__":
    main()
