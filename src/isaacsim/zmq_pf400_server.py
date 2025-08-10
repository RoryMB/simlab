import numpy as np
from pathlib import Path

from isaacsim.core.utils.stage import get_current_stage
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot_motion.motion_generation import LulaKinematicsSolver, ArticulationKinematicsSolver
from omni.isaac.dynamic_control import _dynamic_control
from omni.physx import get_physx_scene_query_interface
from omni.usd.commands.usd_commands import DeletePrimsCommand
from pxr import Sdf, Gf, UsdPhysics

import utils
from zmq_robot_server import ZMQ_Robot_Server


CUSTOM_ASSETS_ROOT_PATH = str(Path(__file__).parent / "../../assets")

class ZMQ_PF400_Server(ZMQ_Robot_Server):
    """Handles ZMQ communication for PF400 robot with integrated control"""

    def __init__(self, simulation_app, robot, robot_name: str, port: int, motion_type: str = "teleport"):
        super().__init__(simulation_app, robot, robot_name, port, motion_type)

        # Motion planning setup
        self.motion_gen_algo = None
        self.motion_gen_solver = None
        self._initialize_motion_generation()

        # Validate pointer prim exists
        self._validate_pointer_prim()

        # Gripper state
        self.gripper_open = True
        self._grab_joint = None  # Track physics joint for gripping

        # Integrated control state
        self.current_action = None  # Current action being executed
        self.target_joints = None   # Target joint positions
        self.target_pose = None     # Target pose for motion planning
        self.is_moving = False      # Whether robot is currently moving
        self.collision_detected = False  # Collision flag
        self.motion_complete = False     # Motion completion flag
        self.collision_actors = None     # Actors involved in collision

        # Raycast parameters (hardcoded for now)
        self.raycast_direction = Gf.Vec3d(0, 0, -1)  # Downward direction
        self.raycast_distance = 0.03  # 3cm detection distance

    def handle_command(self, request):
        """Handle incoming ZMQ command - defer execution to update loop"""
        action = request.get("action", "")

        # Check for collisions
        if self.collision_detected:
            return self.create_error_response(f"Robot halted due to collision: {self.collision_actors}")

        if action == "move_joints":
            joint_angles = request.get("joint_angles", [])

            if len(joint_angles) != 7:
                return self.create_error_response(f"Expected 7 joint angles, got {len(joint_angles)}")

            # Store command for execution in update loop (let Isaac Sim handle validation)
            self.current_action = "move_joints"
            self.target_joints = np.array(joint_angles)
            self.is_moving = True
            self.motion_complete = False

            return self.create_success_response("command queued", joint_angles=joint_angles)

        elif action == "get_joints":
            try:
                joint_positions = self.robot.get_joint_positions()
                return self.create_success_response("joints retrieved", joint_angles=joint_positions.tolist())
            except Exception as e:
                return self.create_error_response(f"Failed to get joint positions: {str(e)}")

        elif action == "gripper_open":
            try:
                self.gripper_open = True
                # Store command for execution in update loop
                self.current_action = "gripper_open"
                self.motion_complete = False
                return self.create_success_response("gripper open queued", gripper_state="open")
            except Exception as e:
                return self.create_error_response(f"Failed to queue gripper open: {str(e)}")

        elif action == "gripper_close":
            try:
                self.gripper_open = False
                # Store command for execution in update loop
                self.current_action = "gripper_close"
                self.motion_complete = False
                return self.create_success_response("gripper close queued", gripper_state="closed")
            except Exception as e:
                return self.create_error_response(f"Failed to queue gripper close: {str(e)}")

        elif action == "get_status":
            try:
                joint_positions = self.robot.get_joint_positions()
                return self.create_success_response(
                    "status retrieved",
                    joint_angles=joint_positions.tolist(),
                    gripper_state="open" if self.gripper_open else "closed",
                    is_moving=self.is_moving,
                    collision_detected=self.collision_detected,
                    motion_complete=self.motion_complete,
                )
            except Exception as e:
                return self.create_error_response(f"Failed to get status: {str(e)}")

        elif action == "goto_pose":
            position = request.get("position", [])
            orientation = request.get("orientation", [])

            if len(position) != 3 or len(orientation) != 4:
                return self.create_error_response("goto_pose requires position [x,y,z] and orientation [w,x,y,z]")

            # Store command for execution in update loop
            self.current_action = "goto_pose"
            self.target_pose = (np.array(position), np.array(orientation))
            self.is_moving = True
            self.motion_complete = False

            return self.create_success_response("goto_pose queued", position=position, orientation=orientation)


        elif action == "get_relative_pose":
            prim_path = request.get("prim_path", "")

            if not prim_path:
                return self.create_error_response("get_relative_pose requires prim_path parameter")

            try:
                stage = get_current_stage()
                target_prim = stage.GetPrimAtPath(prim_path)
                if not target_prim or not target_prim.IsValid():
                    raise RuntimeError(f"Prim not found: {prim_path}")

                robot_prim_path = f"/World/{self.robot_name}"
                robot_prim = stage.GetPrimAtPath(robot_prim_path)
                if not robot_prim or not robot_prim.IsValid():
                    raise RuntimeError(f"Robot prim not found: {robot_prim_path}")

                position, orientation = utils.get_relative_pose(target_prim, robot_prim)
                return self.create_success_response(
                    "relative pose retrieved",
                    position=position.tolist(),
                    orientation=orientation.tolist()
                )
            except Exception as e:
                return self.create_error_response(f"Failed to get relative pose: {str(e)}")

        elif action == "clear_collision":
            self.collision_detected = False
            self.collision_actors = None
            return self.create_success_response("collision cleared")

        else:
            return self.create_error_response(f"Unknown action: {action}")

    def _initialize_motion_generation(self):
        """Initialize motion generation algorithms for the PF400"""
        # PF400 robot configuration paths
        robot_config_dir = CUSTOM_ASSETS_ROOT_PATH + "/temp/robots/pf400"
        robot_description_path = robot_config_dir + "/pf400_descriptor.yaml"
        urdf_path = robot_config_dir + "/pf400.urdf"

        # Verify files exist
        if not Path(robot_description_path).exists():
            raise FileNotFoundError(f"PF400 descriptor not found: {robot_description_path}")
        if not Path(urdf_path).exists():
            raise FileNotFoundError(f"PF400 URDF not found: {urdf_path}")

        # Initialize with IK solver
        self.motion_gen_algo = LulaKinematicsSolver(
            robot_description_path=robot_description_path,
            urdf_path=urdf_path,
        )
        self.motion_gen_solver = ArticulationKinematicsSolver(
            self.robot,
            self.motion_gen_algo,
            'pointer'  # End effector frame name
        )
        print(f"Motion generation initialized for {self.robot_name}")

    def _validate_pointer_prim(self):
        """Validate that the robot has a pointer prim for end effector calculations"""
        stage = get_current_stage()
        robot_prim_path = f"/World/{self.robot_name}"
        pointer_prim_path = f"{robot_prim_path}/pointer"

        pointer_prim = stage.GetPrimAtPath(pointer_prim_path)
        if not pointer_prim or not pointer_prim.IsValid():
            raise RuntimeError(f"Required pointer prim not found at {pointer_prim_path}. "
                             f"Robot {self.robot_name} must have a pointer Xform in its joint hierarchy.")

    def _set_robot_base_pose(self):
        """Update robot base pose for motion planning"""
        if self.motion_gen_algo is None:
            raise RuntimeError(f"Robot {self.robot_name}: Motion generation algorithm not initialized")

        # Get robot base prim
        stage = get_current_stage()
        robot_prim_path = f"/World/{self.robot_name}"
        robot_prim = stage.GetPrimAtPath(robot_prim_path)

        if not robot_prim or not robot_prim.IsValid():
            raise RuntimeError(f"Robot {self.robot_name}: Robot prim not found at {robot_prim_path}")
            
        try:
            robot_pos, robot_rot = utils.get_prim_world_pose(robot_prim)
            self.motion_gen_algo.set_robot_base_pose(robot_pos, robot_rot)
        except Exception as e:
            raise RuntimeError(f"Robot {self.robot_name}: Failed to set robot base pose: {e}") from e

    def _raycast(self, src: Gf.Vec3d, direction: Gf.Vec3d, distance: float, filter_prim_path: str):
        """Perform raycast to detect objects for gripping"""
        physx_query = get_physx_scene_query_interface()

        hits = []
        def ray_func(_hit):
            if _hit.rigid_body.startswith(filter_prim_path):
                return True  # Skip robot itself

            stage = get_current_stage()
            prim = stage.GetPrimAtPath(_hit.rigid_body)
            if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                return True  # Skip non-rigid bodies

            hits.append({
                'hit': True,
                'prim': prim,
                'rigid_body': _hit.rigid_body,
                'position': Gf.Vec3d(*_hit.position),
                'normal': Gf.Vec3d(*_hit.normal),
            })
            return True

        physx_query.raycast_all(src, direction, distance, ray_func)

        # Return closest hit
        if hits:
            hits = sorted(hits, key=lambda x: (src - x['position']).GetLength())
            return hits[0]['prim']
        return None

    def _attach_object(self) -> bool:
        """Attach an object using physics joints (gripping simulation)"""
        if self._grab_joint:
            raise RuntimeError(f"Robot {self.robot_name} already holding something - cannot attach another object")

        stage = get_current_stage()
        pointer_prim_path = f"/World/{self.robot_name}/pointer"
        pointer_prim = stage.GetPrimAtPath(pointer_prim_path)
        
        if not pointer_prim or not pointer_prim.IsValid():
            raise RuntimeError(f"Robot {self.robot_name}: Pointer prim not found at {pointer_prim_path}")

        # Get pointer position and do raycast
        pointer_pos, pointer_rot = utils.get_prim_world_pose(pointer_prim)
        quat = Gf.Quatd(float(pointer_rot[0]), float(pointer_rot[1]), float(pointer_rot[2]), float(pointer_rot[3]))
        rotation = Gf.Rotation(quat)
        direction = rotation.TransformDir(self.raycast_direction)

        hit_prim = self._raycast(Gf.Vec3d(float(pointer_pos[0]), float(pointer_pos[1]), float(pointer_pos[2])), direction, self.raycast_distance,
                                f"/World/{self.robot_name}")
        if not hit_prim:
            raise RuntimeError(f"Robot {self.robot_name}: No object detected for gripping within {self.raycast_distance}m")

        # Create physics joint
        try:
            # Create a unique joint path
            joint_path = pointer_prim.GetPath().AppendChild("grip_joint")
            joint_prim = UsdPhysics.FixedJoint.Define(stage, joint_path)
            
            # Set the bodies to connect
            joint_prim.CreateBody0Rel().SetTargets([pointer_prim.GetPath()])
            joint_prim.CreateBody1Rel().SetTargets([hit_prim.GetPath()])
            
            self._grab_joint = joint_path.pathString
            print(f"Robot {self.robot_name} attached object: {hit_prim.GetPath()}")
            return True
        except Exception as e:
            raise RuntimeError(f"Robot {self.robot_name}: Failed to create physics joint: {e}") from e

    def _detach_object(self) -> bool:
        """Detach the currently held object"""
        if not self._grab_joint:
            return False

        try:
            joint_path = Sdf.Path(self._grab_joint)
            DeletePrimsCommand([joint_path]).do()

            # Wake up the released object
            dc = _dynamic_control.acquire_dynamic_control_interface()
            parent_rb = joint_path.GetParentPath().pathString
            dc.wake_up_rigid_body(dc.get_rigid_body(parent_rb))

            print(f"Robot {self.robot_name} detached object")
            self._grab_joint = None
            return True

        except Exception as e:
            print(f"Robot {self.robot_name}: Error in detach_object: {e}")
            self._grab_joint = None  # Clear invalid joint reference
            raise

    def update(self):
        """Called every simulation frame to execute robot actions"""
        if self.collision_detected:
            # Stop all motion if collision detected, but allow new commands after clear_collision
            if self.is_moving:
                self.halt_motion()
            return

        if self.current_action is None:
            return

        if self.current_action == "move_joints":
            self._execute_move_joints()
        elif self.current_action == "goto_pose":
            self._execute_goto_pose()
        elif self.current_action == "gripper_open":
            self._execute_gripper_open()
        elif self.current_action == "gripper_close":
            self._execute_gripper_close()

    def _execute_move_joints(self):
        """Execute joint movement in simulation"""
        if self.target_joints is None:
            return

        if self.motion_type == "teleport":
            # Teleport directly
            self.robot.set_joint_positions(self.target_joints)
            self.motion_complete = True
            self.is_moving = False
            self.current_action = None
        else:
            # Smooth motion
            action = ArticulationAction(joint_positions=self.target_joints)
            self.robot.apply_action(action)

            # Check if motion is complete
            current_joints = self.robot.get_joint_positions()
            diff = np.abs(current_joints - self.target_joints)
            max_diff = np.max(diff)

            velocities = self.robot.get_joint_velocities()
            max_vel = np.max(np.abs(velocities))

            # Motion is complete when close to target and low velocity
            if max_diff < 0.01 and max_vel < 0.008:
                self.motion_complete = True
                self.is_moving = False
                self.current_action = None
                print(f"Robot {self.robot_name} completed motion")

    def _execute_goto_pose(self):
        """Execute pose-based movement using motion planning"""
        if self.target_pose is None:
            self.current_action = None
            self.is_moving = False
            raise RuntimeError(f"Robot {self.robot_name}: Cannot execute goto_pose - missing target pose")
            
        if self.motion_gen_solver is None:
            self.current_action = None
            self.is_moving = False
            raise RuntimeError(f"Robot {self.robot_name}: Cannot execute goto_pose - motion generation solver not initialized")

        target_position, target_orientation = self.target_pose

        # Update robot base pose for motion planning
        self._set_robot_base_pose()

        # Compute inverse kinematics
        tolerances = (0.001, 0.01)  # Position and orientation tolerances
        try:
            action, success = self.motion_gen_solver.compute_inverse_kinematics(
                target_position, target_orientation, *tolerances
            )

            if not success:
                self.current_action = None
                self.is_moving = False
                raise RuntimeError(f"Robot {self.robot_name}: IK solve failed for target pose {target_position}, {target_orientation}")

            # Apply the computed action
            self.robot.apply_action(action)

            # Check if motion is complete
            if self._close_to_target(action):
                self.motion_complete = True
                self.is_moving = False
                self.current_action = None
                print(f"Robot {self.robot_name} reached target pose")

        except Exception as e:
            self.current_action = None
            self.is_moving = False
            if isinstance(e, RuntimeError):
                raise  # Re-raise RuntimeError as-is
            else:
                raise RuntimeError(f"Robot {self.robot_name}: Error in goto_pose execution: {e}") from e

    def _close_to_target(self, action: ArticulationAction) -> bool:
        """Check if robot is close to target position"""
        if action.joint_positions is None:
            return True

        action_joints = action.joint_positions
        robo_joints = np.array(self.robot.get_joint_positions())[action.joint_indices]

        diff = np.sum(np.abs(action_joints - robo_joints))
        vel = np.sum(np.abs(self.robot.get_joint_velocities()))

        return diff < 0.003 and vel < 0.008

    def _execute_gripper_open(self):
        """Execute gripper opening using physics-based detachment"""
        try:
            success = self._detach_object()
            self.motion_complete = True
            self.current_action = None
            if success:
                print(f"Robot {self.robot_name} opened gripper (detached object)")
            else:
                print(f"Robot {self.robot_name} opened gripper (no object to detach)")
        except Exception as e:
            self.motion_complete = False
            self.current_action = None
            raise RuntimeError(f"Robot {self.robot_name}: Failed to open gripper: {e}") from e

    def _execute_gripper_close(self):
        """Execute gripper closing using physics-based attachment"""
        try:
            success = self._attach_object()
            self.motion_complete = True
            self.current_action = None
            if success:
                print(f"Robot {self.robot_name} closed gripper (attached object)")
            else:
                print(f"Robot {self.robot_name} closed gripper (no object detected)")
        except Exception as e:
            self.motion_complete = False
            self.current_action = None
            raise RuntimeError(f"Robot {self.robot_name}: Failed to close gripper: {e}") from e

    def halt_motion(self):
        """Immediately halt robot motion"""
        # Apply current joint positions to stop motion
        current_joints = self.robot.get_joint_positions()
        action = ArticulationAction(joint_positions=current_joints)
        self.robot.apply_action(action)

        self.is_moving = False
        self.current_action = None
        print(f"Robot {self.robot_name} motion halted")

    def on_collision(self, actor0, actor1):
        """Called when collision is detected involving this robot - recoverable"""
        self.collision_detected = True
        self.collision_actors = f"{actor0} <-> {actor1}"
        print(f"Robot {self.robot_name} collision detected: {self.collision_actors}")

        # Halt current motion but don't permanently disable robot
        self.halt_motion()

        # Clear current action to allow new commands
        self.current_action = None
        self.is_moving = False
        print(f"Robot {self.robot_name} halted due to collision. Use 'clear_collision' to resume operation.")

    def on_motion_complete(self):
        """Called when motion is completed (currently handled internally)"""
        self.motion_complete = True
        self.is_moving = False
        print(f"Robot {self.robot_name} motion completed")
