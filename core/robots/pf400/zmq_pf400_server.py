from pathlib import Path

import numpy as np
import utils
from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf
from zmq_robot_server import ZMQ_Robot_Server


CUSTOM_ASSETS_ROOT_PATH = str((Path(__file__).parent / "../../../assets").resolve())

class ZMQ_PF400_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot with integrated control"""

    def __init__(self, simulation_app, robot, robot_prim_path, robot_name: str, port: int):
        super().__init__(simulation_app, robot, robot_prim_path, robot_name, port)

        # PF400-specific gripper state
        self._grab_joint = None

        # PF400-specific raycast configuration
        self.raycast_direction = Gf.Vec3d(0, 0, -1)  # Downward for PF400
        self.raycast_distance = 0.03  # 3cm reach

        # Initialize PF400-specific motion generation
        self._initialize_motion_generation()

    def handle_command(self, request):
        """Handle incoming ZMQ command"""
        action = request.get("action", "")

        if action == "move_joints":
            joint_positions = request.get("joint_positions", [])
            if not joint_positions:
                joint_positions = request.get("joint_angles", [])  # Support both parameter names
            expected_joints = len(self.robot.get_joint_positions())

            if len(joint_positions) != expected_joints:
                return self.create_error_response(f"Expected {expected_joints} joint positions, got {len(joint_positions)}")

            self.current_action = "move_joints"
            self.target_joints = np.array(joint_positions)
            return self.create_success_response("command queued", joint_positions=joint_positions)

        elif action == "get_joints":
            joint_positions = self.robot.get_joint_positions()
            return self.create_success_response("joints retrieved", data={"joint_positions": joint_positions.tolist()})

        elif action == "get_status":
            joint_positions = self.robot.get_joint_positions()
            is_moving = self.current_action is not None
            motion_complete = self.current_action is None
            status = {
                "robot_name": self.robot_name,
                "joint_positions": joint_positions.tolist(),
                "is_paused": self.is_paused,
                "has_attached_object": bool(self._grab_joint),
                "is_moving": is_moving,
                "motion_complete": motion_complete,
                "collision_detected": self.collision_detected
            }
            return self.create_success_response("status retrieved", data=status)

        elif action == "gripper_open":
            self.current_action = "gripper_open"
            return self.create_success_response("gripper_open queued")

        elif action == "gripper_close":
            self.current_action = "gripper_close"
            return self.create_success_response("gripper_close queued")

        elif action == "goto_pose":
            position = request.get("position", [])
            orientation = request.get("orientation", [])

            if len(position) != 3 or len(orientation) != 4:
                return self.create_error_response("goto_pose requires position [x,y,z] and orientation [w,x,y,z]")

            self.current_action = "goto_pose"
            self.target_pose = (np.array(position), np.array(orientation))
            return self.create_success_response("goto_pose queued", position=position, orientation=orientation)

        elif action == "goto_prim":
            prim_name = request.get("prim_name", "")

            if not prim_name:
                return self.create_error_response("goto_prim requires prim_name parameter")

            # Get prim from stage
            stage = get_current_stage()
            prim = stage.GetPrimAtPath(prim_name)

            if not prim or not prim.IsValid():
                return self.create_error_response(f"Prim not found: {prim_name}")

            # Get prim world position and orientation
            position, orientation = utils.get_xform_world_pose(prim)

            # Queue goto_pose with prim's pose
            self.current_action = "goto_pose"
            self.target_pose = (position, orientation)
            return self.create_success_response("goto_prim queued", prim_name=prim_name, position=position.tolist(), orientation=orientation.tolist())

        elif action == "get_ee_pose":
            # Get end effector (pointer) world position and orientation
            stage = get_current_stage()
            end_effector_prim_path = f"{self.robot_prim_path}/pointer"
            end_effector_prim = stage.GetPrimAtPath(end_effector_prim_path)

            if not end_effector_prim or not end_effector_prim.IsValid():
                return self.create_error_response(f"End effector not found at: {end_effector_prim_path}")

            position, orientation = utils.get_xform_world_pose(end_effector_prim)
            return self.create_success_response("ee_pose retrieved", data={
                "position": position.tolist(),
                "orientation": orientation.tolist(),
            })

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def _get_end_effector_raycast_info(self, end_effector_name: str):
        """Transform end effector prim into world position and raycast direction"""
        stage = get_current_stage()
        end_effector_prim_path = f"{self.robot_prim_path}/{end_effector_name}"
        end_effector_prim = stage.GetPrimAtPath(end_effector_prim_path)

        if not end_effector_prim or not end_effector_prim.IsValid():
            raise RuntimeError(f"End effector prim not found at path: {end_effector_prim_path}")

        # Get end effector position and orientation
        end_effector_pos, end_effector_rot = utils.get_xform_world_pose(end_effector_prim)
        quat = Gf.Quatd(float(end_effector_rot[0]), float(end_effector_rot[1]),
                        float(end_effector_rot[2]), float(end_effector_rot[3]))
        rotation = Gf.Rotation(quat)

        # Transform raycast direction from local to world space
        world_direction = rotation.TransformDir(self.raycast_direction)
        world_position = Gf.Vec3d(float(end_effector_pos[0]), float(end_effector_pos[1]),
                                 float(end_effector_pos[2]))

        return world_position, world_direction

    def execute_gripper_open(self, end_effector_name: str = 'pointer'):
        """Execute gripper opening using physics-based detachment"""
        if not self._grab_joint:
            print(f"Robot {self.robot_name} opened gripper (no object to detach)")
            self.current_action = None
            return

        success = self.detach_object(self._grab_joint)
        if success:
            self._grab_joint = None
            print(f"Robot {self.robot_name} opened gripper (detached object)")
        else:
            print(f"Robot {self.robot_name} failed to open gripper")
        self.current_action = None

    def execute_gripper_close(self, end_effector_name: str = 'pointer'):
        """Execute gripper closing using raycast-based attachment"""
        if self._grab_joint:
            print(f"Robot {self.robot_name} already holding object")
            self.current_action = None
            return

        # Get raycast info using helper method
        world_position, world_direction = self._get_end_effector_raycast_info(end_effector_name)

        # Perform raycast
        hit_prim = self.raycast(world_position, world_direction, self.raycast_distance, self.robot_prim_path)
        if hit_prim:
            # [HACK] Check if the hit object is a microplate
            hit_path = hit_prim.GetPath().pathString
            if "microplate" not in hit_path:
                print(f"Robot {self.robot_name} ignored grasp target (not a microplate): {hit_path}")
                self.current_action = None
                return

            try:
                joint_path = self.attach_object(hit_prim.GetPath().pathString, end_effector_name)
                self._grab_joint = joint_path
                print(f"Robot {self.robot_name} closed gripper (attached object)")
            except Exception as e:
                print(f"Robot {self.robot_name} failed to close gripper: {str(e)}")
        else:
            print(f"Robot {self.robot_name} closed gripper (no object detected)")
        self.current_action = None

    def on_collision(self, actor0, actor1):
        """Handle collision detection - only care about collisions while moving"""

        # Only care about collisions while moving
        if self.current_action is None:
            return

        microplate_path = "/World/microplate"
        involves_microplate = microplate_path in actor0 or microplate_path in actor1
        involves_robot = actor0.startswith(self.robot_prim_path) or actor1.startswith(self.robot_prim_path)
        holding_microplate = self._grab_joint is not None

        # Case 1: Robot hit something that's not the microplate
        if involves_robot and not involves_microplate:
            pass  # Care about this

        # Case 2: Robot touching microplate it's holding
        elif involves_robot and involves_microplate and holding_microplate:
            return  # Ignore

        # Case 3: Microplate we're holding hit something (not the robot)
        elif involves_microplate and not involves_robot and holding_microplate:
            pass  # Care about this

        # Case 4: Any other collision (including microplate when not holding)
        else:
            return  # Ignore

        # Handle the collision
        self.collision_detected = True
        self.collision_actors = f"{actor0} <-> {actor1}"
        print(f"Robot {self.robot_name} collision detected: {self.collision_actors}")

        self.halt_motion()
        self.current_action = None

    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.is_paused:
            return

        if self.current_action is None:
            return

        if self.current_action == "move_joints":
            self.execute_move_joints()
        elif self.current_action == "goto_pose":
            self.execute_goto_pose()
        elif self.current_action == "gripper_open":
            self.execute_gripper_open()
        elif self.current_action == "gripper_close":
            self.execute_gripper_close()

    def _initialize_motion_generation(self):
        """Initialize motion generation algorithms for the PF400"""
        # PF400 robot configuration paths
        robot_config_dir = CUSTOM_ASSETS_ROOT_PATH + "/robots/Brooks/PF400/isaacsim"
        robot_description_path = robot_config_dir + "/descriptor.yaml"
        urdf_path = robot_config_dir + "/PF400.urdf"

        # Use superclass method
        self.initialize_motion_generation(robot_description_path, urdf_path, 'pointer')
